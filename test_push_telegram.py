"""
測試 Telegram 推送功能 (daily_bible_bot)

使用方式：
python test_push_telegram.py
"""

import logging
import os
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS
from bot import push_to_all_telegram_chats

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_audio_to_catbox(audio_path):
    """
    簡易版上傳函數供測試使用
    """
    try:
        with open(audio_path, 'rb') as f:
            data = {'reqtype': 'fileupload'}
            files = {'fileToUpload': f}
            response = requests.post('https://catbox.moe/user/api.php', data=data, files=files, timeout=30)
            if response.status_code == 200:
                return response.text.strip()
            else:
                logging.error(f"Catbox upload failed: {response.text}")
                return None
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return None

def test_telegram_push():
    print("\n" + "="*60)
    print("🧪 測試 Telegram 推送 (Daily Bible Bot)")
    print("="*60 + "\n")
    
    # 測試資料
    test_text = "📖 *測試訊息 from Daily Bible Bot*\n\n這是一則測試訊息，確認 Telegram 整合功能是否正常運作。"
    
    # 尋找測試音檔
    test_audio_url = None
    audio_files = ["daily_message.mp3", "test_daily_message.mp3"]
    
    for f in audio_files:
        if os.path.exists(f):
            print(f"📢 發現測試音檔: {f}")
            print("   上傳中...")
            test_audio_url = upload_audio_to_catbox(f)
            if test_audio_url:
                print(f"   ✅ 上傳成功: {test_audio_url}\n")
            break
            
    if not test_audio_url:
        print("⚠️  未找到測試音檔或上傳失敗，將只發送文字\n")
        
    # 執行推送
    if TELEGRAM_CHAT_IDS and TELEGRAM_BOT_TOKEN:
        print("🚀 開始推送...")
        results = push_to_all_telegram_chats(test_text, test_audio_url)
        success_count = sum(1 for v in results.values() if v)
        print(f"   ✅ 推送完成: {success_count}/{len(results)} 個群組成功")
    else:
        print("⚠️  Telegram 設定未完成 (TOKEN 或 CHAT_IDS 缺失)")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_telegram_push()
