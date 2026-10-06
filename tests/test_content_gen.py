import unittest
from unittest.mock import patch

import content_gen


DEFAULT_EXPOSITION = "NVIDIA NIM 產生的繁體中文靈修短文。\n\n我們一起來禱告：求祢賜我安穩，阿們。"


class FakeNvidiaResponse:
    def __init__(self, content=DEFAULT_EXPOSITION):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {"message": {"content": self.content}}
            ]
        }


class TestGenerateExposition(unittest.TestCase):
    def test_uses_nvidia_nim_model_and_api_key(self):
        verse = {"text": "經文內容", "reference": "約翰福音 1章1節"}

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            return_value=FakeNvidiaResponse(),
        ) as post:
            result = content_gen.generate_exposition(verse)

        self.assertEqual(result, DEFAULT_EXPOSITION)
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], content_gen.NVIDIA_NIM_URL)
        self.assertEqual(
            kwargs["headers"]["Authorization"], "Bearer test-nvidia-key"
        )
        self.assertEqual(kwargs["json"]["model"], content_gen.NVIDIA_NIM_MODEL)
        self.assertEqual(
            kwargs["json"]["chat_template_kwargs"], {"enable_thinking": False}
        )
        prompt = kwargs["json"]["messages"][1]["content"]
        self.assertIn("約 300-400 個中文字", prompt)
        self.assertIn("嚴禁逐字或換標點重複完整經文", prompt)
        self.assertIn("不要重複出處", prompt)
        self.assertIn("禱告必須以「我們一起來禱告」開頭", prompt)
        self.assertEqual(
            content_gen.NVIDIA_NIM_MODEL,
            "nvidia/nemotron-3-ultra-550b-a55b",
        )

    def test_rejects_prompt_leak_after_one_regeneration(self):
        response_content = "提示詞：只輸出靈修正文。"

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(response_content),
                FakeNvidiaResponse(response_content),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": "經文內容", "reference": "以賽亞書 26章4節"}
            )

        self.assertIsNone(result)
        self.assertEqual(post.call_count, content_gen.NVIDIA_NIM_MAX_CONTENT_ATTEMPTS)
        repair_prompt = post.call_args_list[1][1]["json"]["messages"][1]["content"]
        self.assertIn("前一稿含有提示、寫作規格或草稿說明", repair_prompt)
        self.assertIn(response_content, repair_prompt)

    def test_retries_once_when_output_repeats_verse_then_returns_valid_content(self):
        verse_text = "你們當倚靠耶和華直到永遠，因為耶和華是永久的磐石。"
        valid_content = "在等候結果時，先把焦慮交託給神，也踏出今天能做的一步。\n\n我們一起來禱告：求祢賜我安穩的心。"

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(
                    f"你們當倚靠耶和華直到永遠 因為耶和華是永久的磐石！\n\n{valid_content}"
                ),
                FakeNvidiaResponse(valid_content),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": verse_text, "reference": "以賽亞書 26:4"}
            )

        self.assertEqual(result, valid_content)
        self.assertEqual(post.call_count, 2)
        repair_prompt = post.call_args_list[1][1]["json"]["messages"][1]["content"]
        self.assertIn("前一稿重複了經文全文", repair_prompt)
        self.assertIn(verse_text, repair_prompt)
        self.assertIn(valid_content.split("\n\n")[0], repair_prompt)

    def test_repairs_wrong_pronouns_and_missing_prayer(self):
        invalid_content = "耶和華是永久的磐石，妳可以放心。"

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(invalid_content),
                FakeNvidiaResponse(DEFAULT_EXPOSITION),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": "耶和華是我的牧者；我必不致缺乏。", "reference": "詩篇 23:1"}
            )

        self.assertEqual(result, DEFAULT_EXPOSITION)
        repair_prompt = post.call_args_list[1][1]["json"]["messages"][1]["content"]
        self.assertIn("前一稿缺少完整禱告", repair_prompt)
        self.assertIn("敘述神用「祂」", repair_prompt)
        self.assertIn("禱告中稱呼神用「祢」", repair_prompt)

    def test_validation_requires_complete_prayer_and_correct_divine_pronouns(self):
        reflection = "經文提醒我們在等待中仍可以倚靠神。"
        self.assertIsNone(content_gen._validate_exposition(reflection))
        self.assertIsNone(
            content_gen._validate_exposition(f"{reflection}\n\n{content_gen.PRAYER_OPENING}")
        )
        self.assertIsNone(
            content_gen._validate_exposition(
                f"{reflection}\n\n{content_gen.PRAYER_OPENING}：求妳賜我平安，阿們。"
            )
        )
        self.assertIsNone(
            content_gen._validate_exposition(
                f"{reflection}\n\n{content_gen.PRAYER_OPENING}：求你賜我平安，阿們。"
            )
        )
        self.assertIsNone(
            content_gen._validate_exposition(
                f"如果妳正在等候，也請記得照顧自己。\n\n"
                f"{content_gen.PRAYER_OPENING}：求祢賜我平安，阿們。"
            )
        )
        self.assertIsNotNone(
            content_gen._validate_exposition(
                f"{reflection}\n\n{content_gen.PRAYER_OPENING}：求祢賜我平安，阿們。"
            )
        )

    def test_aborts_after_two_overlong_outputs(self):
        overlong_content = "禱" * (content_gen.MAX_EXPOSITION_CHARACTERS + 1)

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(overlong_content),
                FakeNvidiaResponse(overlong_content),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": "某段較長的經文原文", "reference": "以賽亞書 26:4"}
            )

        self.assertIsNone(result)
        self.assertEqual(post.call_count, 2)

    def test_compresses_overlong_draft_with_targeted_rewrite(self):
        verse_text = "你們當倚靠耶和華直到永遠，因為耶和華是永久的磐石。"
        verse_ref = "以賽亞書 26:4"
        overlong_draft = "在漫長等候中，我們可以學習信靠神。" + "神與我們同在。" * 80
        valid_rewrite = "等候時，我們可以把憂慮交託給神，並踏出今天能做的一步。\n\n我們一起來禱告：求祢堅固我的心，阿們。"

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(overlong_draft),
                FakeNvidiaResponse(valid_rewrite),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": verse_text, "reference": verse_ref}
            )

        self.assertEqual(result, valid_rewrite)
        self.assertEqual(post.call_count, 2)
        repair_prompt = post.call_args_list[1][1]["json"]["messages"][1]["content"]
        self.assertIn("請直接壓縮改寫", repair_prompt)
        self.assertIn(f"不得超過 {content_gen.MAX_EXPOSITION_CHARACTERS} 個非空白字元", repair_prompt)
        self.assertIn("保留經文要旨", repair_prompt)
        self.assertIn("一個具體生活處境", repair_prompt)
        self.assertIn("一個可行回應", repair_prompt)
        self.assertIn("完整禱告", repair_prompt)
        self.assertIn(verse_text, repair_prompt)
        self.assertIn(verse_ref, repair_prompt)
        self.assertIn(overlong_draft, repair_prompt)

    def test_validation_rejects_repeated_verse_and_reference(self):
        exposition = "這段經文提醒我們信靠神。"
        self.assertIsNone(
            content_gen._validate_exposition(
                f"{exposition} 你們當倚靠耶和華直到永遠，因為耶和華是永久的磐石。",
                verse_text="你們當倚靠耶和華直到永遠，因為耶和華是永久的磐石。",
            )
        )
        self.assertIsNone(
            content_gen._validate_exposition(
                f"{exposition} 以賽亞書 26：4",
                verse_ref="以賽亞書 26:4",
            )
        )

    def test_validation_rejects_overlong_content(self):
        overlong_content = "禱" * (content_gen.MAX_EXPOSITION_CHARACTERS + 1)

        self.assertIsNone(content_gen._validate_exposition(overlong_content))

    def test_validation_rejects_repair_prompt_leak(self):
        self.assertIsNone(
            content_gen._validate_exposition("修訂要求：所有修訂稿不得超過 450 個非空白字元。")
        )

    def test_retries_transient_nvidia_unavailable(self):
        unavailable = content_gen.requests.Response()
        unavailable.status_code = 503
        unavailable._content = b'{"error":"temporarily unavailable"}'
        success = FakeNvidiaResponse()

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[unavailable, success],
        ) as post, patch.object(content_gen.time, "sleep") as sleep:
            result = content_gen.generate_exposition(
                {"text": "經文內容", "reference": "以賽亞書 26章4節"}
            )

        self.assertEqual(result, DEFAULT_EXPOSITION)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_missing_nvidia_api_key_does_not_call_api(self):
        with patch.object(content_gen, "NVIDIA_API_KEY", None), patch.object(
            content_gen.requests, "post"
        ) as post:
            result = content_gen.generate_exposition(
                {"text": "經文內容", "reference": "約翰福音 1章1節"}
            )

        self.assertIsNone(result)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
