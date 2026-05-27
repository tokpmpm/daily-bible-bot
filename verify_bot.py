import unittest
from unittest.mock import patch, MagicMock
import bot

class TestDailyBibleBot(unittest.TestCase):

    @patch('bot.get_daily_verse')
    @patch('bot.generate_exposition')
    @patch('bot.generate_audio')
    @patch('bot.broadcast_message')
    @patch('bot.send_web_push_notifications')
    @patch('bot.save_to_supabase')
    @patch('bot.upload_audio_to_r2')
    @patch('bot.os.path.getsize')
    @patch('pydub.AudioSegment.from_mp3')
    @patch('bot.TELEGRAM_CHAT_IDS', [])
    @patch('bot.DRY_RUN', False)
    def test_full_flow(
        self,
        mock_audio_segment,
        mock_getsize,
        mock_upload_r2,
        mock_save,
        mock_web_push,
        mock_broadcast,
        mock_audio,
        mock_content,
        mock_scrape,
    ):
        # Setup Mocks
        mock_scrape.return_value = {
            "text": "因為神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。",
            "reference": "提摩太後書 1:7",
            "image_url": "http://example.com/image.png"
        }
        mock_content.return_value = "這是測試用的靈修短文。內容充滿了神學洞見與生活應用..."
        mock_audio.return_value = "daily_message.mp3"
        mock_broadcast.return_value = True
        mock_upload_r2.return_value = "https://audio.example.com/daily-bible/2026/05/27/daily-message.mp3"
        mock_getsize.return_value = 123456
        mock_save.return_value = "record-id"
        
        # Mock Audio Duration
        mock_audio_obj = MagicMock()
        mock_audio_obj.__len__.return_value = 60000 # 60 seconds
        mock_audio_segment.return_value = mock_audio_obj

        # Run the daily task
        bot.run_daily_task()

        # Verify Scraper called
        mock_scrape.assert_called_once()

        # Verify Content Generation called
        mock_content.assert_called_once()

        # Verify Audio Generation called
        mock_audio.assert_called_once()
        
        # Verify R2 upload and Supabase metadata save
        mock_upload_r2.assert_called_once()
        mock_save.assert_called_once()
        save_kwargs = mock_save.call_args[1]
        self.assertEqual(save_kwargs["audio_duration_ms"], 60000)
        self.assertEqual(save_kwargs["audio_size_bytes"], 123456)
        self.assertTrue(save_kwargs["podcast_guid"].startswith("daily-bible-"))

        # Verify Broadcast called
        mock_broadcast.assert_called_once()
        
        # Verify Message Content passed to broadcast
        # args: messages list
        messages = mock_broadcast.call_args[0][0]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]['type'], 'audio')
        self.assertEqual(messages[1]['originalContentUrl'], "https://audio.example.com/daily-bible/2026/05/27/daily-message.mp3")
        self.assertEqual(messages[1]['duration'], 60000)
        
        print("\n✅ Full flow verification passed (MOCKED) with R2 audio upload.")

if __name__ == '__main__':
    unittest.main()
