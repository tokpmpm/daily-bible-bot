import unittest
from unittest.mock import patch

import content_gen


class FakeNvidiaResponse:
    def __init__(self, content="NVIDIA NIM 產生的繁體中文靈修短文。"):
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

        self.assertEqual(result, "NVIDIA NIM 產生的繁體中文靈修短文。")
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
        self.assertEqual(
            content_gen.NVIDIA_NIM_MODEL,
            "nvidia/nemotron-3-ultra-550b-a55b",
        )

    def test_rejects_draft_and_word_count_notes(self):
        response_content = (
            "用戶想要一篇靈修短文。\n起草內容：\n"
            "字數檢查：約 135 字。\n正文內容。"
        )

        with patch.object(content_gen, "NVIDIA_API_KEY", "test-nvidia-key"), patch.object(
            content_gen.requests,
            "post",
            return_value=FakeNvidiaResponse(response_content),
        ):
            result = content_gen.generate_exposition(
                {"text": "經文內容", "reference": "以賽亞書 26章4節"}
            )

        self.assertIsNone(result)

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
