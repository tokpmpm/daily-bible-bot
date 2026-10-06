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
        self.assertIn("約 280-350 個中文字", prompt)
        self.assertEqual(content_gen.MAX_EXPOSITION_CHARACTERS, 650)
        self.assertIn("正文寫成三段自然文字", prompt)
        self.assertIn("每段約 2-4 句", prompt)
        self.assertIn("全文不逐段分配字數", prompt)
        self.assertIn("開頭直接說明經文意思", prompt)
        self.assertIn("不要先用「耶穌說：", prompt)
        self.assertIn("不添加經文沒有提供的歷史背景", prompt)
        self.assertIn("不擴張成經文沒有支持的神學斷言", prompt)
        self.assertIn("正文不需重複", prompt)
        self.assertIn("請清楚標明是假設", prompt)
        self.assertIn("不可寫成作者親身經歷或見證", prompt)
        self.assertIn("避免像清單般羅列多種處境", prompt)
        self.assertIn("不要把信心說成實現願望的保證", prompt)
        self.assertIn("不要保證疾病必定痊癒", prompt)
        self.assertIn("若經文談信心與禱告，不要把信心說成", prompt)
        self.assertNotIn("馬可福音 11:24", prompt)
        self.assertIn("不要只是重述正文", prompt)
        self.assertIn("敘述神用「祂」", prompt)
        self.assertIn("禱告中稱呼神用「祢」", prompt)
        self.assertIn("最後以「我們一起來禱告」開頭", prompt)
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
        self.assertIn("禱告中一律用「祢」", repair_prompt)

    def test_rewrites_fabricated_personal_healing_testimony(self):
        fabricated_testimony = (
            "前幾天深夜，女兒高燒，我和妻子為她禱告。"
            "隔天清晨，她的燒退了。"
        )
        valid_rewrite = (
            "信心不是要求神照我們的意思行，而是在不確定中仍倚靠祂。"
            "我們可以把掛慮帶到神面前，也尋求身邊人的支持。\n\n"
            "我們一起來禱告：求祢扶持正在擔心的人，阿們。"
        )

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            side_effect=[
                FakeNvidiaResponse(fabricated_testimony + "\n\n" + DEFAULT_EXPOSITION),
                FakeNvidiaResponse(valid_rewrite),
            ],
        ) as post:
            result = content_gen.generate_exposition(
                {"text": "凡你們禱告祈求的，無論是甚麼，只要信是得著的，就必得著。", "reference": "馬可福音 11:24"}
            )

        self.assertEqual(result, valid_rewrite)
        self.assertEqual(post.call_count, 2)
        repair_prompt = post.call_args_list[1][1]["json"]["messages"][1]["content"]
        self.assertIn("移除像作者親身經歷或見證的敘述", repair_prompt)
        self.assertIn("不要把禱告寫成保證願望實現或疾病痊癒", repair_prompt)
        self.assertIn("假設", repair_prompt)

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
                f"{reflection}\n\n{content_gen.PRAYER_OPENING}：求祂赦免我，阿們。"
            )
        )
        self.assertIsNone(
            content_gen._validate_exposition(
                f"{reflection}\n\n{content_gen.PRAYER_OPENING}：願祂賜下平安，阿們。"
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
        self.assertIsNotNone(
            content_gen._validate_exposition(
                f"祂是我的磐石。\n\n{content_gen.PRAYER_OPENING}：求祢賜我平安，阿們。"
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
        overlong_draft = "在漫長等候中，我們可以學習信靠神。" + "神與我們同在。" * 100
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
        self.assertIn("自然收短", repair_prompt)
        self.assertIn(f"不得超過 {content_gen.MAX_EXPOSITION_CHARACTERS} 個非空白字元", repair_prompt)
        self.assertIn("全文以約 280-350 個中文字", repair_prompt)
        self.assertIn("三段自然文字", repair_prompt)
        self.assertIn("保留經文核心", repair_prompt)
        self.assertIn("自然的生活連結", repair_prompt)
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
        mark_verse = "凡你們禱告祈求的，無論是甚麼，只要信是得著的，就必得著。"
        variant_quote = (
            "凡你們禱告祈求的，無論是甚麼，只要信是得着的，就必得着。\n\n"
            "我們一起來禱告：求祢幫助我們信靠祢，阿們。"
        )
        self.assertIsNone(
            content_gen._validate_exposition(variant_quote, verse_text=mark_verse)
        )
        self.assertEqual(
            content_gen._normalize_for_comparison("看着裏面的臺灣和衆人爲神祈求"),
            content_gen._normalize_for_comparison("看著裡面的台灣和眾人為神祈求"),
        )

    def test_validation_rejects_near_full_verse_quote_but_allows_short_phrases(self):
        mark_verse = (
            "所以我告訴你們，凡你們禱告祈求的，無論是甚麼，"
            "只要信是得著的，就必得著。"
        )
        near_full_quote = (
            "凡你們禱告祈求的，無論是甚麼，只要信是得着的，就必得着。\n\n"
            "我們一起來禱告：求祢幫助我們信靠祢，阿們。"
        )
        normalized_source = content_gen._normalize_for_comparison(mark_verse)
        normalized_near_quote = content_gen._normalize_for_comparison(near_full_quote)
        matched_length = content_gen._longest_common_contiguous_length(
            normalized_source, normalized_near_quote
        )
        self.assertGreaterEqual(matched_length, content_gen.MIN_NEAR_VERBATIM_CHARACTERS)
        self.assertGreaterEqual(
            matched_length * 100,
            len(normalized_source) * content_gen.NEAR_VERBATIM_SOURCE_PERCENT,
        )
        issues = content_gen._exposition_issues(near_full_quote, verse_text=mark_verse)
        self.assertIn("repeated_verse", issues)
        self.assertIsNone(
            content_gen._validate_exposition(near_full_quote, verse_text=mark_verse)
        )

        ordinary_phrase = (
            "凡你們禱告祈求的，無論是甚麼，提醒我們可以把掛慮帶到神面前。\n\n"
            "我們一起來禱告：求祢帶領我今天的腳步，阿們。"
        )
        ordinary_issues = content_gen._exposition_issues(
            ordinary_phrase, verse_text=mark_verse
        )
        self.assertNotIn("repeated_verse", ordinary_issues)

        longer_phrase = "凡你們禱告祈求的，無論是甚麼，只要信是得"
        self.assertGreaterEqual(
            len(content_gen._normalize_for_comparison(longer_phrase)),
            content_gen.MIN_NEAR_VERBATIM_CHARACTERS,
        )
        self.assertLess(
            len(content_gen._normalize_for_comparison(longer_phrase)) * 100,
            len(normalized_source) * content_gen.NEAR_VERBATIM_SOURCE_PERCENT,
        )
        partial_quote = (
            f"經文中的「{longer_phrase}」提醒我們把掛慮帶到神面前。\n\n"
            "我們一起來禱告：求祢扶持我，阿們。"
        )
        partial_issues = content_gen._exposition_issues(
            partial_quote, verse_text=mark_verse
        )
        self.assertNotIn("repeated_verse", partial_issues)

        short_verse = "耶和華是我的牧者，我必不致缺乏。"
        short_phrase = (
            "耶和華是我的牧者，這句話提醒我們可以在疲倦時尋求安歇。\n\n"
            "我們一起來禱告：求祢扶持我，阿們。"
        )
        short_issues = content_gen._exposition_issues(
            short_phrase, verse_text=short_verse
        )
        self.assertNotIn("repeated_verse", short_issues)

    def test_validation_rejects_overlong_content(self):
        overlong_content = "禱" * (content_gen.MAX_EXPOSITION_CHARACTERS + 1)

        self.assertIsNone(content_gen._validate_exposition(overlong_content))

        prayer = "\n\n我們一起來禱告：求祢賜我平安，阿們。"
        remaining = content_gen.MAX_EXPOSITION_CHARACTERS - sum(
            not char.isspace() for char in prayer
        )
        boundary_content = "信靠神" * (remaining // 3) + "信" * (remaining % 3) + prayer
        self.assertEqual(
            sum(not char.isspace() for char in boundary_content),
            content_gen.MAX_EXPOSITION_CHARACTERS,
        )
        self.assertIsNotNone(content_gen._validate_exposition(boundary_content))

    def test_validation_rejects_repair_prompt_leak(self):
        self.assertIsNone(
            content_gen._validate_exposition(
                f"修訂要求：所有修訂稿不得超過 {content_gen.MAX_EXPOSITION_CHARACTERS} 個非空白字元。"
            )
        )

    def test_rejects_current_prompt_fragments_without_blocking_devotional_prose(self):
        prompt_fragments = (
            "全文以約 280-350 個中文字為目標",
            "每段約 2-4 句",
            "三段自然文字",
            "不要先用「耶穌說：",
            "不添加經文沒有提供的歷史背景",
            "不擴張成經文沒有支持的神學斷言",
            "開頭直接說明經文意思",
            "請寫一篇可直接發布和朗讀",
            "經文（只供理解",
            "出處（只供理解",
            "若是虛構情境，請清楚標明是假設",
            "不可寫成作者親身經歷或見證",
            "若經文談信心與禱告，不要把信心說成實現願望的保證",
            "生活例子可以明確標示為假設",
            "不必套固定套路",
            "避免像清單般羅列多種處境",
            "讓解經、生活連結和禱告自然銜接",
        )
        for fragment in prompt_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    "prompt_leak",
                    content_gen._exposition_issues(fragment),
                )

        natural_devotional = (
            "這段經文提醒我們，在日常選擇中也能尋求神的引導。\n\n"
            "我們一起來禱告：求祢幫助我今天做出合宜的選擇，阿們。"
        )
        self.assertEqual(content_gen._exposition_issues(natural_devotional), [])

    def test_rejects_obvious_fabricated_testimony_and_promised_outcomes(self):
        fabricated_testimony = (
            "前幾天深夜，女兒高燒，我和妻子為她禱告。"
            "隔天清晨，她的燒退了。\n\n"
            "我們一起來禱告：求祢保守家人，阿們。"
        )
        issues = content_gen._exposition_issues(fabricated_testimony)
        self.assertIn("personal_testimony", issues)
        self.assertIn("guaranteed_outcome", issues)
        self.assertIsNone(content_gen._validate_exposition(fabricated_testimony))

        wish_guarantee = (
            "只要相信並禱告，心裡的願望一定會實現；主一定醫治病人。\n\n"
            "我們一起來禱告：求祢帶領我們，阿們。"
        )
        self.assertIn(
            "guaranteed_outcome",
            content_gen._exposition_issues(wish_guarantee),
        )
        self.assertIsNone(content_gen._validate_exposition(wish_guarantee))

    def test_accepts_clearly_labeled_hypothetical_life_example(self):
        hypothetical = (
            "假設有一位母親，深夜陪伴生病的孩子，心裡雖然擔心，"
            "仍將憂慮帶到神面前，也尋求親友和醫療人員的支持。\n\n"
            "我們一起來禱告：求祢陪伴正在等候的家庭，賜下平安，阿們。"
        )
        self.assertEqual(content_gen._exposition_issues(hypothetical), [])

        mixed = hypothetical.split("\n\n", 1)[0] + (
            "。其實前幾天深夜，我和妻子為女兒禱告，隔天她就退燒了。\n\n"
            "我們一起來禱告：求祢安慰掛心的人，阿們。"
        )
        mixed_issues = content_gen._exposition_issues(mixed)
        self.assertIn("personal_testimony", mixed_issues)
        self.assertIn("guaranteed_outcome", mixed_issues)

        faithful_caveat = (
            "這不是說我們所求的一定實現，也不表示疾病必定痊癒；"
            "經文邀請我們在祈求中仍信靠神。\n\n"
            "我們一起來禱告：求祢扶持我們在等候中仍有盼望，阿們。"
        )
        self.assertEqual(content_gen._exposition_issues(faithful_caveat), [])

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
