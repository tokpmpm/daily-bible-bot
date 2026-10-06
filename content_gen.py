import requests
import logging
import time
from config import NVIDIA_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_NIM_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
NVIDIA_NIM_MAX_ATTEMPTS = 3
NVIDIA_NIM_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_PUBLISHABLE_MARKERS = (
    "用戶想要",
    "用戶希望",
    "限制條件：",
    "起草內容：",
    "字數檢查：",
    "第一段（固定）",
    "第二段（解經",
    "第三段（應用",
    "第四段（禱告",
    "<think>",
    "</think>",
)


def _validate_exposition(content):
    """Reject reasoning or drafting notes before they reach users or TTS."""
    if not isinstance(content, str) or not content.strip():
        logging.error("NVIDIA NIM returned an empty exposition.")
        return None

    content = content.strip()
    if any(marker.casefold() in content.casefold() for marker in NON_PUBLISHABLE_MARKERS):
        logging.error(
            "NVIDIA NIM output contained internal planning text; refusing publication."
        )
        return None

    return content

def generate_exposition(verse_data):
    """
    Generates a 350-word exposition for the given verse using NVIDIA NIM.
    """
    if not NVIDIA_API_KEY:
        logging.error("NVIDIA_API_KEY is not set.")
        return None

    verse_text = verse_data['text']
    verse_ref = verse_data['reference']

    prompt = f"""
    你是對聖經有深厚認識的解經家。請為今天的經文撰寫一篇靈修短文。
    
    經文：{verse_text}
    出處：{verse_ref}
    
    嚴格要求：
    1. 總字數：必須嚴格控制在 280-350 字之間，絕對不可超過 400 字！
    2. 對象：對聖經有中等程度了解的基督徒
    3. 語言：繁體中文（台灣用語）
    4. 風格：溫暖、精簡有力
    
    結構與字數分配：
    第一段（經文）：{verse_text}{verse_ref}
    第二段（解經）：約 130-150 字 - 簡要解釋經文的神學意涵
    第三段（應用）：約 80-100 字 - 一個簡短的現代生活實例
    第四段（禱告）：約 60-80 字 - 以「我們一起來禱告」開頭的簡短禱告
    
    格式注意：
    - 嚴禁使用任何 Markdown 符號（如 *、#、- 等）
    - 純文字，分段撰寫
    
    ⚠️ 重要提醒：最終正文控制在 280-350 字，絕對不可超過 400 字。

    輸出規則：只輸出可直接發布和朗讀的靈修正文。不可輸出草稿、計畫、思考、分析、字數檢查、格式說明、段落標籤或以上任何指示。
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NVIDIA_API_KEY}"
    }
    data = {
        "model": NVIDIA_NIM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一位資深的聖經教師，擅長用溫暖的語氣講解聖經真理。"
                    "只輸出最終靈修正文；不要輸出思考、分析、計畫、草稿、"
                    "字數計算、格式說明、段落標籤或提示內容。"
                ),
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    for attempt in range(1, NVIDIA_NIM_MAX_ATTEMPTS + 1):
        response = None
        try:
            response = requests.post(
                NVIDIA_NIM_URL,
                headers=headers,
                json=data,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            content = _validate_exposition(content)
            if not content:
                return None
            logging.info("Successfully generated exposition with NVIDIA NIM.")
            return content
        except requests.RequestException as error:
            response = getattr(error, "response", None) or response
            status_code = getattr(response, "status_code", None)
            retryable = (
                status_code in NVIDIA_NIM_RETRYABLE_STATUS_CODES
                or isinstance(error, (requests.Timeout, requests.ConnectionError))
            )
            if retryable and attempt < NVIDIA_NIM_MAX_ATTEMPTS:
                retry_delay = min(2 ** attempt, 8)
                logging.warning(
                    "NVIDIA NIM request failed transiently (status=%s; attempt %d/%d); "
                    "retrying in %d seconds.",
                    status_code,
                    attempt,
                    NVIDIA_NIM_MAX_ATTEMPTS,
                    retry_delay,
                )
                time.sleep(retry_delay)
                continue

            logging.error("Error generating content: %s", error)
            if response is not None:
                logging.error("Response: %s", response.text)
            return None
        except Exception as error:
            logging.error("Error generating content: %s", error)
            if response is not None:
                logging.error("Response: %s", response.text)
            return None

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
