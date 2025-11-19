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
        
        # Set mock return values
        mock_gen_text.return_value = (
            "今日靈修：提摩太後書 1章7節\n"
            "因為神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。\n\n"
            "【測試模式】這是一篇測試用的靈修短文。\n"
            "此模式下不會呼叫 OpenAI API，因此不消耗額度。\n\n"
            "重點測試：\n"
            "1. 爬蟲是否正常抓取每日經文。\n"
            "2. 音檔上傳是否成功 (catbox.moe)。\n"
            "3. LINE 訊息 (文字 + 語音) 是否正常發送。\n\n"
            "我們一起來禱告：\n"
            "親愛的天父，感謝祢賜給我們剛強的心。奉耶穌的名禱告，阿們。"
        )
        mock_gen_audio.return_value = dummy_audio_path
        
        # Run the bot
        bot.run_daily_task()
        
    logging.info("Integration Test Complete.")

if __name__ == "__main__":
    run_integration_test()
