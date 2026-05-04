import requests
import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

book_mapping = {
    "Genesis": "創世記", "Exodus": "出埃及記", "Leviticus": "利未記", "Numbers": "民數記", "Deuteronomy": "申命記",
    "Joshua": "約書亞記", "Judges": "士師記", "Ruth": "路得記", "1 Samuel": "撒母耳記上", "2 Samuel": "撒母耳記下",
    "1 Kings": "列王紀上", "2 Kings": "列王紀下", "1 Chronicles": "歷代志上", "2 Chronicles": "歷代志下",
    "Ezra": "以斯拉記", "Nehemiah": "尼希米記", "Esther": "以斯帖記", "Job": "約伯記", "Psalm": "詩篇", "Psalms": "詩篇",
    "Proverbs": "箴言", "Ecclesiastes": "傳道書", "Song of Solomon": "雅歌", "Isaiah": "以賽亞書", "Jeremiah": "耶利米書",
    "Lamentations": "耶利米哀歌", "Ezekiel": "以西結書", "Daniel": "但以理書", "Hosea": "何西阿書", "Joel": "約珥書",
    "Amos": "阿摩司書", "Obadiah": "俄巴底亞書", "Jonah": "約拿書", "Micah": "彌迦書", "Nahum": "那鴻書",
    "Habakkuk": "哈巴谷書", "Zephaniah": "西番雅書", "Haggai": "哈該書", "Zechariah": "撒迦利亞書", "Malachi": "瑪拉基書",
    "Matthew": "馬太福音", "Mark": "馬可福音", "Luke": "路加福音", "John": "約翰福音", "Acts": "使徒行傳",
    "Romans": "羅馬書", "1 Corinthians": "哥林多前書", "2 Corinthians": "哥林多後書", "Galatians": "加拉太書",
    "Ephesians": "以弗所書", "Philippians": "腓立比書", "Colossians": "歌羅西書", "1 Thessalonians": "帖撒羅尼迦前書",
    "2 Thessalonians": "帖撒羅尼迦後書", "1 Timothy": "提摩太前書", "2 Timothy": "提摩太後書", "Titus": "提多書",
    "Philemon": "腓利門書", "Hebrews": "希伯來書", "James": "雅各書", "1 Peter": "彼得前書", "2 Peter": "彼得後書",
    "1 John": "約翰一書", "2 John": "約翰二書", "3 John": "約翰三書", "Jude": "猶大書", "Revelation": "啟示錄"
}

def get_daily_verse():
    """
    Fetches the Verse of the Day reference from Bible.com and 
    retrieves the Traditional Chinese (CUV) text via bible-api.com.
    Returns a dictionary with 'text', 'reference', and 'image_url'.
    """
    try:
        url = "https://www.bible.com/zh-TW/verse-of-the-day"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
        if not m:
            logging.warning("Could not find __NEXT_DATA__ in HTML. Bible.com structure might have changed.")
            return None
            
        data = json.loads(m.group(1)).get('props', {}).get('pageProps', {})
        ref_title = data.get('referenceTitle', {}).get('title', '')
        if not ref_title:
            logging.warning("Could not find referenceTitle in data.")
            return None
            
        # Example ref_title: "Matthew 9:37-38"
        match = re.match(r'^([\d\sA-Za-z]+)\s+([\d:,-]+)$', ref_title)
        if not match:
            logging.warning(f"Could not parse reference format: {ref_title}")
            return None
            
        eng_book = match.group(1).strip()
        verses_ref = match.group(2).strip()
        
        chi_book = book_mapping.get(eng_book, eng_book)
        api_query = f"{chi_book} {verses_ref}"
        
        # Fetch actual text from bible-api.com
        api_url = f"https://bible-api.com/{api_query}?translation=cuv"
        api_res = requests.get(api_url, timeout=10)
        api_res.raise_for_status()
        
        api_data = api_res.json()
        verse_text = api_data.get('text', '').strip()
        
        # Format Reference: change 1:7-8 to 1章7-8節
        if ':' in verses_ref:
            ch, vs = verses_ref.split(':', 1)
            formatted_ref = f"{chi_book} {ch}章{vs}節"
        else:
            formatted_ref = f"{chi_book} {verses_ref}"
            
        # Extract Image URL
        image_url = None
        images = data.get('images', [])
        if images and len(images) > 0:
            renditions = images[0].get('renditions', [])
            if renditions:
                image_url = renditions[-1].get('url')
                if image_url and image_url.startswith('//'):
                    image_url = 'https:' + image_url

        logging.info(f"Successfully fetched verse: {formatted_ref}")
        
        return {
            "text": verse_text,
            "reference": formatted_ref,
            "image_url": image_url
        }
        
    except Exception as e:
        logging.error(f"Error fetching daily verse: {e}")
        return None

if __name__ == "__main__":
    # Manual test
    data = get_daily_verse()
    if data:
        print("Fetched Data:")
        print(f"Text: {data['text']}")
        print(f"Reference: {data['reference']}")
        print(f"Image: {data['image_url']}")
    else:
        print("Failed to fetch data.")
