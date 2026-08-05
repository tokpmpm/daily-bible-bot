import requests
import json
import re
import logging
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

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

_BOOK_LOOKUP = {book.lower(): book for book in book_mapping}
_BOOK_PATTERN = "|".join(
    re.escape(book) for book in sorted(book_mapping, key=len, reverse=True)
)
_REFERENCE_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9])(?P<book>{_BOOK_PATTERN})\s+"
    rf"(?P<verses>\d+:\d+(?:\s*[-–—,]\s*\d+)*)"
    rf"\s*(?:\([^)]+\))?",
    re.IGNORECASE,
)


def _normalize_reference(book: str, verses: str) -> str:
    canonical_book = _BOOK_LOOKUP.get(book.lower(), book.strip())
    normalized_verses = re.sub(r"\s*[–—]\s*", "-", verses)
    normalized_verses = re.sub(r"\s*,\s*", ",", normalized_verses)
    return f"{canonical_book} {normalized_verses.strip()}"


def _find_reference(text: str) -> str:
    if not text:
        return ""
    match = _REFERENCE_PATTERN.search(text)
    if not match:
        return ""
    return _normalize_reference(match.group("book"), match.group("verses"))


def _extract_reference_and_data(html: str):
    """Extract a Bible reference from both old and current Bible.com markup."""
    data = {}

    # Legacy Next.js payload used by the original implementation.
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1)).get("props", {}).get("pageProps", {})
            reference_title = data.get("referenceTitle", "")
            if isinstance(reference_title, dict):
                reference_title = reference_title.get("title", "")
            reference = _find_reference(str(reference_title))
            if reference:
                return reference, data, "__NEXT_DATA__"
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            logging.warning("Could not parse Bible.com __NEXT_DATA__: %s", error)

    soup = BeautifulSoup(html, "html.parser")

    # Some versions expose the reference in the document title.
    if soup.title:
        reference = _find_reference(soup.title.get_text(" ", strip=True))
        if reference:
            return reference, data, "html-title"

    # Current Bible.com markup renders text such as "Luke 16:10 (NIV)"
    # inside a normal link. Search likely content elements before the whole page
    # so the main verse is selected before the previous-days list.
    for element in soup.find_all(["a", "span", "p", "h1", "h2", "h3"]):
        reference = _find_reference(element.get_text(" ", strip=True))
        if reference:
            return reference, data, "visible-content"

    reference = _find_reference(soup.get_text(" ", strip=True))
    if reference:
        return reference, data, "page-text"

    return "", data, "not-found"


def _daily_verse_urls(now=None):
    """Build deterministic Bible.com URLs using the user's Taiwan date."""
    taipei_now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    day_of_year = taipei_now.timetuple().tm_yday
    return [
        f"https://www.bible.com/verse-of-the-day?day={day_of_year}",
        f"https://www.bible.com/zh-TW/verse-of-the-day?day={day_of_year}",
        "https://www.bible.com/verse-of-the-day",
    ]


def get_daily_verse(now=None):
    """
    Fetch the Verse of the Day reference from Bible.com and retrieve the
    Traditional Chinese (CUV) text via bible-api.com.

    The optional ``now`` argument exists for deterministic tests; production
    callers can continue calling this function without arguments.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
        "Cache-Control": "no-cache",
    }

    ref_title = ""
    data = {}

    for url in _daily_verse_urls(now):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            ref_title, data, source = _extract_reference_and_data(response.text)
            if ref_title:
                logging.info(
                    "Bible.com reference extracted via %s from %s: %s",
                    source,
                    response.url,
                    ref_title,
                )
                break

            soup = BeautifulSoup(response.text, "html.parser")
            page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
            logging.warning(
                "No Bible reference found from %s "
                "(status=%s, content_type=%s, body_length=%s, title=%r)",
                response.url,
                response.status_code,
                response.headers.get("Content-Type", ""),
                len(response.text),
                page_title,
            )
        except requests.RequestException as error:
            logging.warning("Bible.com request failed for %s: %s", url, error)

    if not ref_title:
        logging.error("Could not find today's Bible reference after all fallbacks.")
        return None

    match = re.fullmatch(r"([\d\sA-Za-z]+)\s+([\d:,-]+)", ref_title)
    if not match:
        logging.warning("Could not parse reference format: %s", ref_title)
        return None

    eng_book = match.group(1).strip()
    verses_ref = match.group(2).strip()
    chi_book = book_mapping.get(eng_book, eng_book)
    api_query = f"{chi_book} {verses_ref}"

    try:
        api_url = f"https://bible-api.com/{quote(api_query)}?translation=cuv"
        api_response = requests.get(api_url, timeout=15)
        api_response.raise_for_status()
        api_data = api_response.json()
    except (requests.RequestException, ValueError) as error:
        logging.error("Error fetching CUV verse text: %s", error)
        return None

    verse_text = api_data.get("text", "").strip()
    if not verse_text:
        logging.error("Bible API returned an empty verse for %s", api_query)
        return None

    chapter, verses = verses_ref.split(":", 1)
    formatted_ref = f"{chi_book} {chapter}章{verses}節"

    image_url = None
    images = data.get("images", []) if isinstance(data, dict) else []
    if images:
        renditions = images[0].get("renditions", [])
        if renditions:
            image_url = renditions[-1].get("url")
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

    logging.info("Successfully fetched verse: %s", formatted_ref)
    return {
        "text": verse_text,
        "reference": formatted_ref,
        "image_url": image_url,
    }


if __name__ == "__main__":
    result = get_daily_verse()
    if result:
        print("Fetched Data:")
        print(f"Text: {result['text']}")
        print(f"Reference: {result['reference']}")
        print(f"Image: {result['image_url']}")
    else:
        print("Failed to fetch data.")
