import requests
import logging
import json
import os
import time
import uuid
from config import LINE_CHANNEL_ACCESS_TOKEN
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

            # Upload to catbox.moe
            with open(audio_path, 'rb') as f:
                data = {'reqtype': 'fileupload'}
                files = {'fileToUpload': f}
                response = requests.post('https://catbox.moe/user/api.php', data=data, files=files)
                
                if response.status_code == 200:
                    audio_url = response.text.strip()
                    logging.info(f"Audio uploaded to: {audio_url}")
                else:
                    logging.error(f"Failed to upload audio: {response.status_code} {response.text}")
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

if __name__ == "__main__":
    run_daily_task()
