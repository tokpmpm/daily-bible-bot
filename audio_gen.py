import requests
import logging
import time
from config import OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "nova"
TTS_INSTRUCTIONS = (
    "請使用自然的台灣華語朗讀。特別注意中文破音字與聖經語境："
    "重新、重生讀作 chong；重量讀作 zhong；長老讀作 zhang；"
    "長久讀作 chang；行走讀作 xing；音樂讀作 yue；喜樂讀作 le。"
    "語速穩定，像每日靈修旁白。"
)

def generate_audio(text, output_path="daily_message.mp3"):
    """
    Generates audio from text using OpenAI TTS API.
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
        "model": TTS_MODEL,
        "input": text,
        "voice": TTS_VOICE,
        "instructions": TTS_INSTRUCTIONS
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
                
            logging.info(f"Successfully generated audio at {output_path}")
            return output_path
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logging.error(f"Error generating audio after {max_retries} attempts: {e}")
                if 'response' in locals():
                    logging.error(f"Response: {response.text}")
                return None
            time.sleep(2)  # Wait before retry

if __name__ == "__main__":
    # Manual test
    text = "這是每日聖經靈修的測試語音。神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。"
    
    print(f"\n{'='*60}")
    print("🎤 TTS Test")
    print(f"{'='*60}")
    print(f"Model: {TTS_MODEL}")
    print(f"Voice: {TTS_VOICE}")
    print(f"{'='*60}\n")
    
    output = generate_audio(text)
    if output:
        print(f"✅ Audio generated: {output}")
    else:
        print("❌ Failed to generate audio.")
