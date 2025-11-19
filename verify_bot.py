import unittest
from unittest.mock import patch, MagicMock
import bot
import json
import os

class TestDailyBibleBot(unittest.TestCase):

    @patch('bot.get_daily_verse')
    @patch('bot.generate_exposition')
    @patch('bot.generate_audio')
    @patch('bot.broadcast_message')
    @patch('bot.requests.post')
    @patch('pydub.AudioSegment.from_mp3')
    def test_full_flow(self, mock_audio_segment, mock_post, mock_broadcast, mock_audio, mock_content, mock_scrape):
        # Setup Mocks
        mock_scrape.return_value = {
            "text": "因為神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。",
            "reference": "提摩太後書 1:7",
            "image_url": "http://example.com/image.png"
        }
        mock_content.return_value = "這是測試用的靈修短文。內容充滿了神學洞見與生活應用..."
        mock_audio.return_value = "daily_message.mp3"
        mock_broadcast.return_value = True
        
        # Mock Audio Duration
        mock_audio_obj = MagicMock()
        mock_audio_obj.__len__.return_value = 60000 # 60 seconds
        mock_audio_segment.return_value = mock_audio_obj

        # Mock Upload Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "https://files.catbox.moe/test.mp3"
        mock_post.return_value = mock_response

        # Run the daily task
        with patch('builtins.open', unittest.mock.mock_open(read_data=b"data")) as mock_file:
            bot.run_daily_task()

        # Verify Scraper called
        mock_scrape.assert_called_once()

        # Verify Content Generation called
        mock_content.assert_called_once()

        # Verify Audio Generation called
        mock_audio.assert_called_once()
        
        # Verify Upload called
        # requests.post should be called for upload
        # args: url, data, files
        upload_called = False
        for call in mock_post.call_args_list:
            if 'catbox.moe' in call[0][0]:
                upload_called = True
                break
        self.assertTrue(upload_called, "Audio upload should be attempted via catbox.moe")

        # Verify Broadcast called
        mock_broadcast.assert_called_once()
        
        # Verify Message Content passed to broadcast
        # args: messages list
        messages = mock_broadcast.call_args[0][0]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]['type'], 'audio')
        self.assertEqual(messages[1]['originalContentUrl'], "https://files.catbox.moe/test.mp3")
        self.assertEqual(messages[1]['duration'], 60000)
        
        print("\n✅ Full flow verification passed (MOCKED) with Audio Upload (catbox.moe).")

if __name__ == '__main__':
    unittest.main()
