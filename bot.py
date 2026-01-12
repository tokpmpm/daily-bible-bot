import requests
import logging
import json
import os
import time
import uuid
from datetime import datetime
from config import (
    LINE_CHANNEL_ACCESS_TOKEN, 
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_IDS,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    VAPID_PRIVATE_KEY,
    VAPID_PUBLIC_KEY
)
from scraper import get_daily_verse
from content_gen import generate_exposition
from audio_gen import generate_audio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def broadcast_message(messages):
    """
    Broadcasts messages to all users using LINE Messaging API.
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logging.error("LINE_CHANNEL_ACCESS_TOKEN is not set.")
        return False

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "X-Line-Retry-Key": str(uuid.uuid4())
    }
    data = {
        "messages": messages
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        logging.info("Successfully broadcasted messages.")
        return True
    except Exception as e:
        logging.error(f"Error broadcasting messages: {e}")
        if 'response' in locals():
             logging.error(f"Response: {response.text}")
        return False

def push_to_telegram_chat(chat_id: str, text: str, audio_url: str = None) -> bool:
    """
    Push messages to a specific Telegram chat using Telegram Bot API.
    
    Args:
        chat_id: Telegram chat ID (can be group, channel, or user)
        text: Text message to send
        audio_url: Optional audio file URL to send
    
    Returns:
        True if successful, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN is not set.")
        return False

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    try:
        # Send text message with Markdown formatting
        text_url = f"{base_url}/sendMessage"
        text_data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(text_url, json=text_data, timeout=30)
        response.raise_for_status()
        logging.info(f"Successfully sent text to Telegram chat: {chat_id}")
        
        # Send audio if available
        if audio_url:
            audio_url_endpoint = f"{base_url}/sendAudio"
            audio_data = {
                "chat_id": chat_id,
                "audio": audio_url,
                "title": "每日靈修"
            }
            audio_response = requests.post(audio_url_endpoint, json=audio_data, timeout=60)
            audio_response.raise_for_status()
            logging.info(f"Successfully sent audio to Telegram chat: {chat_id}")
        
        return True
    except Exception as e:
        logging.error(f"Error pushing to Telegram chat {chat_id}: {e}")
        if 'response' in locals():
            logging.error(f"Response: {response.text}")
        return False


def push_to_all_telegram_chats(text: str, audio_url: str = None) -> dict:
    """
    Push messages to all configured Telegram chats.
    
    Returns:
        Dictionary with chat_id as key and success status as value
    """
    results = {}
    
    if not TELEGRAM_CHAT_IDS:
        logging.warning("No Telegram chat IDs configured. Set TELEGRAM_CHAT_IDS in .env file.")
        return results
    
    for chat_id in TELEGRAM_CHAT_IDS:
        success = push_to_telegram_chat(chat_id, text, audio_url)
        results[chat_id] = success
    
    return results


def save_to_supabase(verse_data: dict, exposition: str, audio_url: str) -> str:
    """
    儲存每日內容至 Supabase
    Returns: 新建立的記錄 ID，失敗則返回 None
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logging.warning("Supabase credentials not set. Skipping save.")
        return None
    
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "verse_text": verse_data['text'],
        "verse_reference": verse_data['reference'],
        "exposition": exposition,
        "audio_url": audio_url or "",
        "view_count": 0,
        "play_count": 0
    }
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/daily_bible",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            record_id = result[0]['id'] if result else None
            logging.info(f"Successfully saved to Supabase: {record_id}")
            return record_id
        else:
            logging.error(f"Failed to save to Supabase: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error saving to Supabase: {e}")
        return None


def send_web_push_notifications(title: str, body: str, url: str = None):
    """
    發送 Web Push 通知給所有訂閱者
    """
    if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, VAPID_PRIVATE_KEY]):
        logging.warning("Web Push credentials not set. Skipping push notifications.")
        return
    
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logging.warning("pywebpush not installed. Skipping push notifications.")
        return
    
    # 從 Supabase 取得所有訂閱者
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/push_subscribers?select=subscription",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logging.error(f"Failed to get subscribers: {response.text}")
            return
        
        subscribers = response.json()
        
        if not subscribers:
            logging.info("No push subscribers found.")
            return
        
        logging.info(f"Sending push notifications to {len(subscribers)} subscribers")
        
        payload = json.dumps({
            "title": title,
            "body": body[:100] + "..." if len(body) > 100 else body,
            "url": url or "https://your-site.github.io/daily-bible/"
        })
        
        success_count = 0
        for sub in subscribers:
            try:
                webpush(
                    subscription_info=sub['subscription'],
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": "mailto:admin@example.com"}
                )
                success_count += 1
            except WebPushException as e:
                logging.warning(f"Failed to send push: {e}")
                # 如果訂閱已失效，可以從資料庫刪除
                if e.response and e.response.status_code in [404, 410]:
                    logging.info("Subscription expired, should be removed")
        
        logging.info(f"Web Push complete: {success_count}/{len(subscribers)} succeeded")
        
    except Exception as e:
        logging.error(f"Error sending web push: {e}")


def run_daily_task():
    logging.info("Starting daily task...")

    # 1. Scrape Verse
    verse_data = get_daily_verse()
    if not verse_data:
        logging.error("Failed to get daily verse. Aborting.")
        return

    logging.info(f"Verse fetched: {verse_data['reference']}")

    # 2. Generate Content
    exposition = generate_exposition(verse_data)
    if not exposition:
        logging.error("Failed to generate exposition. Aborting.")
        return

    logging.info("Exposition generated.")

    # 3. Generate Audio
    # Note: LINE requires a public URL for audio. 
    # Since we are running locally/script, we can't easily host the file for LINE to pick up 
    # without an external storage service (S3, GCS, etc.).
    # For now, we will generate the file locally as requested, but we might not be able to send it 
    # as a native Audio message without a URL.
    audio_text = f"今日靈修。{verse_data['reference']}。{verse_data['text']}。{exposition}"
    # Truncate audio text if too long to save cost/time, or use full. 
    # OpenAI TTS is cheap, but let's keep it reasonable.
    audio_path = generate_audio(audio_text[:4096]) # API limit check
    
    if audio_path:
        logging.info(f"Audio generated at {audio_path}")
    else:
        logging.warning("Audio generation failed.")

    # 4. Upload Audio and Get Duration
    audio_url = None
    audio_duration = 0
    
    if audio_path:
        try:
            # Get Duration
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(audio_path)
            audio_duration = len(audio) # Duration in milliseconds
            logging.info(f"Audio duration: {audio_duration}ms")

            # Upload to catbox.moe with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(audio_path, 'rb') as f:
                        data = {'reqtype': 'fileupload'}
                        files = {'fileToUpload': f}
                        response = requests.post('https://catbox.moe/user/api.php', data=data, files=files, timeout=20)
                        
                        if response.status_code == 200:
                            audio_url = response.text.strip()
                            logging.info(f"Audio uploaded to catbox.moe: {audio_url}")
                            break # Success, exit loop
                        else:
                            logging.warning(f"Failed to upload audio to catbox (Attempt {attempt+1}/{max_retries}): {response.status_code} {response.text}")
                except Exception as e:
                     logging.warning(f"Error uploading audio to catbox (Attempt {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(3) # Wait before retry

            # Fallback to 0x0.st if catbox failed
            if not audio_url:
                logging.warning("Catbox upload failed. Attempting fallback to 0x0.st...")
                try:
                    with open(audio_path, 'rb') as f:
                        files = {'file': f}
                        response = requests.post('https://0x0.st', files=files, timeout=30)
                        if response.status_code == 200:
                            audio_url = response.text.strip()
                            logging.info(f"Audio uploaded to 0x0.st: {audio_url}")
                        else:
                            logging.error(f"Failed to upload to 0x0.st: {response.status_code} {response.text}")
                except Exception as e:
                    logging.error(f"Error uploading to 0x0.st: {e}")

            if not audio_url:
                logging.error("Failed to upload audio to all services. Proceeding without audio.")
        except Exception as e:
            logging.error(f"Error processing audio for LINE: {e}")

    # 5. Construct LINE Messages
    messages = [
        {
            "type": "text",
            "text": f"{verse_data['text']}\n\n{exposition}"
        }
    ]

    if audio_url and audio_duration > 0:
        messages.append({
            "type": "audio",
            "originalContentUrl": audio_url,
            "previewUrl": audio_url, # LINE uses the same URL for preview if not specified otherwise
            "duration": audio_duration
        })

    # 6. Send via LINE
    # Only send if we are in production or have tokens.
    if LINE_CHANNEL_ACCESS_TOKEN != "your_line_channel_access_token":
        broadcast_message(messages)
    else:
        logging.info("Dry run complete. Messages not sent (Token not set).")
        print("=== Message Content ===")
        print(json.dumps(messages, indent=2, ensure_ascii=False))

    # 7. Push to all configured Telegram chats
    if TELEGRAM_CHAT_IDS:
        # Format text for Telegram (Markdown)
        telegram_text = f"📖 *每日靈修*\n\n{verse_data['text']}\n\n{exposition}"
        telegram_results = push_to_all_telegram_chats(telegram_text, audio_url)
        telegram_success_count = sum(1 for v in telegram_results.values() if v)
        logging.info(f"Telegram push complete: {telegram_success_count}/{len(telegram_results)} chats succeeded")
    else:
        logging.info("No Telegram chats configured.")

    # 8. 儲存至 Supabase
    record_id = save_to_supabase(verse_data, exposition, audio_url)
    if record_id:
        logging.info(f"Content saved to Supabase with ID: {record_id}")
    
    # 9. 發送 Web Push 通知
    if record_id:
        send_web_push_notifications(
            title="📖 今日靈修",
            body=f"{verse_data['reference']}: {verse_data['text'][:50]}...",
            url="https://your-site.github.io/daily-bible/"
        )
    
    logging.info("Daily task completed successfully!")


if __name__ == "__main__":
    run_daily_task()
