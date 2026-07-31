import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import bot


class FakeAudio:
    def __len__(self):
        return 12345


class FakeTelegramResponse:
    status_code = 200
    text = '{"ok":true}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class TestFullTestMode(unittest.TestCase):
    def _formal_mocks(self):
        return {
            name: MagicMock(name=name)
            for name in (
                "upload_audio_to_r2",
                "broadcast_message",
                "push_to_all_telegram_chats",
                "save_to_supabase",
                "send_web_push_notifications",
            )
        }

    def test_full_test_success_returns_before_formal_publishers(self):
        verse = {"reference": "以弗所書 3章20-21節", "text": "神能照着運行在我們心裏的大力。"}
        exposition = "這是由 OpenAI 產生的完整測試解經內容。"
        formal = self._formal_mocks()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_file.write(b"non-empty mp3")
            audio_path = audio_file.name

        try:
            with patch.object(bot, "RUN_MODE", "full_test"), \
                 patch.object(bot, "DRY_RUN", False), \
                 patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token"), \
                 patch.object(bot, "TELEGRAM_TEST_CHAT_ID", "test-chat"), \
                 patch.object(bot, "TELEGRAM_CHAT_IDS", []), \
                 patch.object(bot, "get_daily_verse", return_value=verse) as get_verse, \
                 patch.object(bot, "generate_exposition", return_value=exposition) as gen_text, \
                 patch.object(bot, "generate_audio", return_value=audio_path) as gen_audio, \
                 patch("pydub.AudioSegment.from_mp3", return_value=FakeAudio()), \
                 patch.object(
                     bot,
                     "send_full_test_to_telegram",
                     return_value=True,
                 ) as send_test, \
                 patch.multiple(bot, **formal):
                result = bot.run_daily_task()

            self.assertTrue(result)
            get_verse.assert_called_once_with()
            gen_text.assert_called_once_with(verse)
            gen_audio.assert_called_once_with(
                "今日靈修。以弗所書 3章20-21節。神能照着運行在我們心裏的大力。。"
                + exposition
            )
            send_test.assert_called_once_with(
                "test-chat",
                "🧪 每日靈修完整流程測試\n\n"
                "以弗所書 3章20-21節\n"
                "神能照着運行在我們心裏的大力。\n\n"
                + exposition,
                audio_path,
            )
            for formal_mock in formal.values():
                formal_mock.assert_not_called()
        finally:
            os.unlink(audio_path)

    def test_full_test_telegram_failure_returns_false_and_stops(self):
        verse = {"reference": "箴言 18章21節", "text": "生死在舌頭的權下。"}
        formal = self._formal_mocks()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_file.write(b"non-empty mp3")
            audio_path = audio_file.name

        try:
            with patch.object(bot, "RUN_MODE", "full_test"), \
                 patch.object(bot, "DRY_RUN", False), \
                 patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token"), \
                 patch.object(bot, "TELEGRAM_TEST_CHAT_ID", "test-chat"), \
                 patch.object(bot, "get_daily_verse", return_value=verse), \
                 patch.object(bot, "generate_exposition", return_value="解經"), \
                 patch.object(bot, "generate_audio", return_value=audio_path), \
                 patch("pydub.AudioSegment.from_mp3", return_value=FakeAudio()), \
                 patch.object(bot, "send_full_test_to_telegram", return_value=False), \
                 patch.multiple(bot, **formal):
                result = bot.run_daily_task()

            self.assertFalse(result)
            for formal_mock in formal.values():
                formal_mock.assert_not_called()
        finally:
            os.unlink(audio_path)

    def test_test_telegram_sender_uses_only_local_audio_and_test_chat(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_file.write(b"mp3 data")
            audio_path = audio_file.name

        try:
            with patch.object(bot, "TELEGRAM_BOT_TOKEN", "test-token"), \
                 patch.object(bot, "TELEGRAM_TEST_CHAT_ID", "test-chat"), \
                 patch.object(
                     bot.requests,
                     "post",
                     return_value=FakeTelegramResponse(),
                 ) as post:
                self.assertTrue(
                    bot.send_full_test_to_telegram(
                        "test-chat", "完整原文", audio_path
                    )
                )

            self.assertEqual(post.call_count, 2)
            first_args, first_kwargs = post.call_args_list[0]
            self.assertTrue(first_args[0].endswith("/sendMessage"))
            self.assertEqual(first_kwargs["data"], {"chat_id": "test-chat", "text": "完整原文"})
            self.assertNotIn("parse_mode", first_kwargs["data"])

            second_args, second_kwargs = post.call_args_list[1]
            self.assertTrue(second_args[0].endswith("/sendAudio"))
            self.assertEqual(second_kwargs["data"]["title"], "每日靈修完整流程測試")
            self.assertEqual(second_kwargs["data"]["performer"], "Daily Bible Bot")
            self.assertIn("Supabase", second_kwargs["data"]["caption"])
            self.assertEqual(second_kwargs["files"]["audio"][0], "daily_message.mp3")
        finally:
            os.unlink(audio_path)


if __name__ == "__main__":
    unittest.main()
