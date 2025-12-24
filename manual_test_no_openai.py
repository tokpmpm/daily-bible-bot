import unittest
from unittest.mock import patch
import bot
import logging
from pydub import AudioSegment
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_dummy_mp3(filename="dummy.mp3"):
    """Creates a 1-second silent MP3 file for testing."""
    if not os.path.exists(filename):
        logging.info(f"Creating dummy audio file: {filename}")
        silent = AudioSegment.silent(duration=1000) # 1 second
        silent.export(filename, format="mp3")
    return filename

def run_integration_test():
    """
    Runs the bot daily task with OpenAI components mocked.
    Real: Scraper, Audio Upload, LINE Broadcast.
    Mock: Content Generation, Audio Generation.
    """
    logging.info("Starting Integration Test (No OpenAI)...")
    
    # 1. Create dummy audio
    dummy_audio_path = create_dummy_mp3()
    
    # 2. Patch OpenAI functions
    with patch('bot.generate_exposition') as mock_gen_text, \
         patch('bot.generate_audio') as mock_gen_audio:
        
        # Set mock side_effect to use real verse data
        def mock_generate_exposition(verse_data):
            return (
                f"今日靈修：{verse_data['reference']}\n"
                f"{verse_data['text']}\n\n"
                "【測試模式】這是一篇測試用的靈修短文。\n"
                "此模式下不會呼叫 OpenAI API，因此不消耗額度。\n\n"
                "重點測試：\n"
                "1. 爬蟲是否正常抓取每日經文。\n"
                "2. 音檔上傳是否成功 (catbox.moe)。\n"
                "3. LINE 訊息 (文字 + 語音) 是否正常發送。\n\n"
                "我們一起來禱告：\n"
                "親愛的天父，感謝祢賜給我們剛強的心。奉耶穌的名禱告，阿們。"
            )
        mock_gen_text.side_effect = mock_generate_exposition
        mock_gen_audio.return_value = dummy_audio_path
        
        # Mock broadcast_message to just print
        with patch('bot.broadcast_message') as mock_broadcast:
            def print_messages(messages):
                logging.info("--- TEST MODE: Printing Messages (Not sending to LINE) ---")
                for msg in messages:
                    if msg['type'] == 'text':
                        print(f"[Text Message]:\n{msg['text']}\n")
                    elif msg['type'] == 'audio':
                        print(f"[Audio Message]:\nURL: {msg['originalContentUrl']}\nDuration: {msg['duration']}ms\n")
                logging.info("--- End of Messages ---")
                return True
            
            mock_broadcast.side_effect = print_messages
            
            # Run the bot
            bot.run_daily_task()
        
    logging.info("Integration Test Complete.")

if __name__ == "__main__":
    run_integration_test()
