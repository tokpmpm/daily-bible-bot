import requests
import logging
import time
from config import OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        "model": "tts-1",
        "input": text,
        "voice": "nova"  # Female voice, speaks Mandarin well
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
