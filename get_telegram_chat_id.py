"""
Telegram Chat ID 取得工具

使用方式：
1. 在 .env 設定 TELEGRAM_BOT_TOKEN
2. 執行此程式
3. 在 Telegram 群組或頻道中傳送任意訊息（將 bot 加入群組）
4. 程式會顯示接收到的 Chat ID
5. 將 Chat ID 複製到 .env 的 TELEGRAM_CHAT_IDS
"""

import requests
import time
import logging
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_updates(offset=None):
    """
    Get updates from Telegram Bot API.
    """
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN is not set in .env file.")
        return None
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error getting updates: {e}")
        return None


def main():
    print("\n" + "="*60)
    print("🤖 Telegram Chat ID 取得工具")
    print("="*60)
    print("\n請按照以下步驟操作：")
    print("1. 將你的 Telegram Bot 加入目標群組或頻道")
    print("2. 在群組/頻道中傳送任意訊息（例如：/start 或 hello）")
    print("3. 本程式會自動偵測並顯示 Chat ID")
    print("\n正在監聽訊息...\n")
    
    last_update_id = 0
    seen_chats = set()
    
    try:
        while True:
            result = get_updates(offset=last_update_id + 1 if last_update_id else None)
            
            if result and result.get("ok") and result.get("result"):
                for update in result["result"]:
                    last_update_id = max(last_update_id, update["update_id"])
                    
                    # Extract chat information
                    message = update.get("message") or update.get("channel_post")
                    if message and "chat" in message:
                        chat = message["chat"]
                        chat_id = chat["id"]
                        chat_type = chat["type"]
                        chat_title = chat.get("title", chat.get("username", "Unknown"))
                        
                        if chat_id not in seen_chats:
                            seen_chats.add(chat_id)
                            print(f"\n✅ 發現新的 Chat:")
                            print(f"   Chat ID: {chat_id}")
                            print(f"   類型: {chat_type}")
                            print(f"   名稱: {chat_title}")
                            print(f"\n   請將此 Chat ID 加入 .env 的 TELEGRAM_CHAT_IDS")
                            print(f"   範例: TELEGRAM_CHAT_IDS={chat_id}")
                            print("-" * 60)
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n程式已停止。")
        if seen_chats:
            print(f"\n總共發現 {len(seen_chats)} 個 Chat ID:")
            for chat_id in seen_chats:
                print(f"  - {chat_id}")
        else:
            print("\n未發現任何 Chat ID。請確認：")
            print("  1. Bot Token 是否正確")
            print("  2. Bot 是否已加入群組")
            print("  3. 群組中是否有傳送訊息")


if __name__ == "__main__":
    main()
