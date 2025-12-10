import requests
import logging
import time
import asyncio
from datetime import datetime
from config import OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# TTS Voice Rotation Configuration
# Rotates daily: Day 1 -> HsiaoChen, Day 2 -> YunJhe, Day 3 -> OpenAI Nova, Day 4 -> HsiaoChen...
VOICE_ROTATION = [
    {"type": "edge", "voice": "zh-TW-HsiaoChenNeural", "name": "曉臻 (Edge TTS)"},
    {"type": "edge", "voice": "zh-TW-YunJheNeural", "name": "雲哲 (Edge TTS)"},
    {"type": "openai", "voice": "nova", "name": "Nova (OpenAI)"},
]

def get_today_voice():
    """
    Get today's voice based on day of year rotation.
    Returns the voice config for today.
    """
    day_of_year = datetime.now().timetuple().tm_yday
    voice_index = day_of_year % len(VOICE_ROTATION)
    voice = VOICE_ROTATION[voice_index]
    logging.info(f"Today's voice: {voice['name']} (Day {day_of_year}, Index {voice_index})")
    return voice

async def generate_edge_tts(text, voice_id, output_path):
    """
    Generate audio using Edge TTS (Microsoft, free unlimited).
    """
    try:
        import edge_tts
    except ImportError:
        logging.error("edge_tts not installed. Run: pip install edge-tts")
        return None
    
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)
        logging.info(f"Successfully generated Edge TTS audio at {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error generating Edge TTS audio: {e}")
        return None

def generate_openai_tts(text, voice, output_path):
    """
    Generate audio using OpenAI TTS API.
    """
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set.")
        return None

    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "tts-1",
        "input": text,
        "voice": voice
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                
            logging.info(f"Successfully generated OpenAI TTS audio at {output_path}")
            return output_path
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logging.error(f"Error generating OpenAI TTS audio after {max_retries} attempts: {e}")
                if 'response' in locals():
                    logging.error(f"Response: {response.text}")
                return None
            time.sleep(2)

def generate_audio(text, output_path="daily_message.mp3"):
    """
    Generates audio from text using rotating TTS voices.
    Rotates daily between: HsiaoChen (Edge), YunJhe (Edge), Nova (OpenAI)
    """
    voice_config = get_today_voice()
    
    if voice_config["type"] == "edge":
        # Use Edge TTS
        return asyncio.run(generate_edge_tts(text, voice_config["voice"], output_path))
    else:
        # Use OpenAI TTS
        return generate_openai_tts(text, voice_config["voice"], output_path)

if __name__ == "__main__":
    # Manual test
    text = "這是每日聖經靈修的測試語音。神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。"
    
    print(f"\n{'='*60}")
    print("🎤 TTS Voice Rotation Test")
    print(f"{'='*60}")
    
    voice = get_today_voice()
    print(f"Today's voice: {voice['name']}")
    print(f"Voice type: {voice['type']}")
    print(f"Voice ID: {voice['voice']}")
    print(f"{'='*60}\n")
    
    output = generate_audio(text)
    if output:
        print(f"✅ Audio generated: {output}")
    else:
        print("❌ Failed to generate audio.")
