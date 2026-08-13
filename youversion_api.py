import logging
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

import scraper

API_BASE = "https://api.youversion.com/v1"
CUNP_VERSION_ID = 46

PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


def _headers():
    app_key = os.environ.get("YOUVERSION_APP_KEY", "").strip()
    if not app_key:
        raise RuntimeError("YOUVERSION_APP_KEY is not configured")
    return {"X-YVP-App-Key": app_key, "Accept": "application/json"}


def _request_json(url, headers):
    response = requests.get(url, headers=headers, timeout=20)
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        body = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"YouVersion API HTTP {response.status_code} for {url}: {body}"
        ) from error
    try:
        return response.json()
    except ValueError as error:
        body = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"YouVersion API returned non-JSON for {url}: {body}"
        ) from error


def _day_of_year(now=None):
    taipei_now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    return taipei_now.timetuple().tm_yday


def _reference_from_cunp_title(title):
    if not title:
        return ""
    for english_book, chinese_book in scraper.book_mapping.items():
        match = re.search(
            rf"{re.escape(chinese_book)}\s+(\d+:\d+(?:\s*[-–—]\s*\d+)*)",
            title,
        )
        if match:
            return scraper._normalize_reference(english_book, match.group(1))
    return ""


def _fetch_cunp_page(passage_id):
    cunp_url = (
        f"https://www.bible.com/zh-TW/bible/{CUNP_VERSION_ID}/"
        f"{passage_id}.CUNP-%E7%A5%9E"
    )
    response = requests.get(cunp_url, headers=PAGE_HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    reference, _, source, _ = scraper._extract_reference_and_data(response.text)
    if not reference:
        reference = _reference_from_cunp_title(title)

    text = scraper._extract_cunp_text(response.text)
    if not text:
        visible_text = soup.get_text(" ", strip=True)
        if sum("\u4e00" <= char <= "\u9fff" for char in visible_text) < 20:
            raise ValueError("Bible.com CUNP page did not contain enough Chinese text")
        text = visible_text

    if not reference or not text:
        raise ValueError(
            f"Could not extract CUNP reference/text from Bible.com (title={title[:160]!r})"
        )

    logging.info(
        "CUNP passage fetched via Bible.com deterministic URL: %s (source=%s, text_length=%s)",
        reference,
        source or "cunp-title",
        len(text),
    )
    return reference, text


def get_daily_verse(now=None):
    """Get today's VOTD from YouVersion API, then CUNP text from its fixed passage URL."""
    day = _day_of_year(now)
    votd = _request_json(f"{API_BASE}/verse_of_the_days/{day}", _headers())
    passage_id = str(votd.get("passage_id", "")).strip()
    if not passage_id:
        raise ValueError(f"YouVersion VOTD response has no passage_id: {votd}")

    reference, text = _fetch_cunp_page(passage_id)
    logging.info(
        "YouVersion VOTD: day=%s passage=%s reference=%s text_length=%s",
        day,
        passage_id,
        reference,
        len(text),
    )
    return {
        "text": text,
        "reference": reference,
        "image_url": None,
        "passage_id": passage_id,
        "day": day,
    }
