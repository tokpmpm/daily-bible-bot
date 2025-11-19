import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_daily_verse():
    """
    Fetches the Verse of the Day from Bible.com (Traditional Chinese).
    Returns a dictionary with 'text', 'reference', and 'image_url'.
    """
    url = "https://www.bible.com/zh-TW"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Strategy 1: Use the specific classes found by the browser agent
        # Verse Text
        # H2 classes: text-text-light dark:text-text-dark text-19 tracking-tight font-aktiv-grotesk font-medium mbs-2 mbe-0.5 leading-loose
        # We'll use a subset of these that seem unique enough
        verse_text_el = soup.find('h2', class_=lambda x: x and 'text-19' in x and 'leading-loose' in x)
        
        # Verse Reference
        # DIV classes: text-11 mbe-3
        verse_ref_el = soup.find('div', class_=lambda x: x and 'text-11' in x and 'mbe-3' in x)

        # Image URL
        # The browser agent found it in a style attribute or img tag.
        # We'll look for the og:image first as a fallback, or specific VOTD images.
        image_url = None
        
        # Try to find the specific VOTD image
        # It often appears in a meta tag or a specific container
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image['content']

        if not verse_text_el or not verse_ref_el:
            logging.warning("Could not find verse elements with primary selectors. Dumping HTML for debugging if needed.")
            # Fallback strategy could be added here if needed
            return None

        verse_text = verse_text_el.get_text(strip=True)
        verse_ref = verse_ref_el.get_text(strip=True)

        # Clean up text if it contains "每日經文" (Verse of the Day) prefix
        if "每日經文" in verse_text:
            verse_text = verse_text.replace("每日經文", "").strip()

        # Format Reference: Remove version and change 1:7 to 1章7節
        # Example: "提摩太後書 1:7 (CUNP-神)" -> "提摩太後書 1章7節"
        import re
        # Remove version (content in parentheses at the end)
        verse_ref = re.sub(r'\s*\(.*?\)$', '', verse_ref)
        # Change colon to Chapter/Verse
        verse_ref = re.sub(r'(\d+):(\d+)', r'\1章\2節', verse_ref)

        logging.info(f"Successfully fetched verse: {verse_ref}")
        
        return {
            "text": verse_text,
            "reference": verse_ref,
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
