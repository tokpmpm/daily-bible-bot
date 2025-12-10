import requests
import json
import logging
from config import OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_exposition(verse_data):
    """
    Generates a 400-word exposition for the given verse using OpenAI API.
    """
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set.")
        return None

    verse_text = verse_data['text']
    verse_ref = verse_data['reference']

    prompt = f"""
    你是對聖經有深厚認識的解經家。請為今天的經文撰寫一篇靈修短文。
    
    經文：{verse_text}
    出處：{verse_ref}
    
    要求：
    1. 對象：對聖經有中等程度了解的基督徒。
    2. 字數：約 400 字。
    3. 語言：繁體中文（台灣用語）。
    4. 內容：必須包含現代生活實例，幫助讀者應用經文。
    5. 風格：溫暖、激勵人心，包含神學洞見與生活應用。
    6. 格式：
       - 開頭第一行：{verse_text}
       - 內文：分段撰寫，易於閱讀。
       - 嚴禁使用任何 Markdown 符號（如 *、#、- 等），純文字即可。
       - 禱告：請以「我們一起來禱告」作為禱告部分的開頭。
    """

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "你是一位資深的聖經教師，擅長用溫暖的語氣講解聖經真理。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        logging.info("Successfully generated exposition.")
        return content
    except Exception as e:
        logging.error(f"Error generating content: {e}")
        if 'response' in locals():
             logging.error(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    # Manual test
    mock_data = {
        "text": "因為神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。",
        "reference": "提摩太後書 1:7"
    }
    content = generate_exposition(mock_data)
    if content:
        print("Generated Content:")
        print(content)
    else:
        print("Failed to generate content.")
