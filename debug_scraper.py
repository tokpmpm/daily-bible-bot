import requests
from bs4 import BeautifulSoup

def debug_scraper():
    urls = [
        "https://www.bible.com/zh-TW",
        "https://www.bible.com/zh-TW/verse-of-the-day",
        "https://www.bible.com/zh-TW/verse-of-the-day/324"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    for url in urls:
        print(f"\n--- Checking URL: {url} ---")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Check what the current selector finds
            verse_text_el = soup.find('h2', class_=lambda x: x and 'text-19' in x and 'leading-loose' in x)
            verse_ref_el = soup.find('div', class_=lambda x: x and 'text-11' in x and 'mbe-3' in x)
            
            if verse_text_el:
                print(f"Current Selector Text: {verse_text_el.get_text(strip=True)}")
            else:
                print("Current Selector Text: NOT FOUND")
                
            if verse_ref_el:
                print(f"Current Selector Ref: {verse_ref_el.get_text(strip=True)}")
            else:
                print("Current Selector Ref: NOT FOUND")

            # 2. Dump all H2s to see if we can find the real verse
            print("\n--- All H2 Elements ---")
            for i, h2 in enumerate(soup.find_all('h2')):
                print(f"H2 #{i}: {h2.get_text(strip=True)} | Classes: {h2.get('class')}")

            # 3. Dump all Divs that look like references
            print("\n--- Potential Reference Divs ---")
            for i, div in enumerate(soup.find_all('div', class_=lambda x: x and 'text-11' in x)):
                 print(f"Div #{i}: {div.get_text(strip=True)} | Classes: {div.get('class')}")

            if "verse-of-the-day" in url:
                print("\n--- All Text Content (First 500 chars) ---")
                print(soup.get_text(strip=True)[:500])
                print("\n--- All Links ---")
                for a in soup.find_all('a', href=True):
                    if 'bible' in a['href']:
                        print(f"Link: {a.get_text(strip=True)} -> {a['href']}")

        except Exception as e:
            print(f"Error checking {url}: {e}")

if __name__ == "__main__":
    debug_scraper()
