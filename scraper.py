import html
import json
import logging
import re
from datetime import datetime
from urllib.parse import quote, urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    "1 John": "約翰一書", "2 John": "約翰二書", "3 John": "約翰三書", "Jude": "猶大書", "Revelation": "啟示錄",
}

_BOOK_LOOKUP = {book.lower(): book for book in book_mapping}
_BOOK_PATTERN = "|".join(re.escape(book) for book in sorted(book_mapping, key=len, reverse=True))
_REFERENCE_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9])(?P<book>{_BOOK_PATTERN})\s+"
    rf"(?P<verses>\d+:\d+(?:\s*[-–—,]\s*\d+)*)"
    rf"\s*(?:\([^)]+\))?",
    re.IGNORECASE,
)
_OSIS_PATTERN = re.compile(r"/(?:bible|compare)/(?:\d+/)?(?P<osis>[1-3A-Z]{3}\.\d+\.\d+(?:-\d+)?)", re.I)
_CUNP_LINK_PATTERN = re.compile(r"/zh-TW/bible/\d+/[^\"']*CUNP", re.I)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


class ScraperSourceError(Exception):
    """Base error for a source that cannot provide usable scraper data."""


class AntiBotChallenge(ScraperSourceError):
    """Raised when a site returns an anti-bot challenge instead of content."""


class ReferenceUnavailable(ScraperSourceError):
    """Raised when a provider cannot provide today's verse reference."""


_CUV_API_BOOK_ALIASES = {
    # bible-api.com uses formal CUV book names for these books.
    "約翰一書": "約翰壹書",
    "約翰二書": "約翰貳書",
    "約翰三書": "約翰參書",
}


def _is_antibot_challenge(html_text: str) -> bool:
    """Detect common challenge pages that still return HTTP 200."""
    body = (html_text or "").lower()
    return (
        "client challenge" in body
        or "/_fs-ch" in body
        or "cf-chl-" in body
    )


def _get_html(url: str, *, headers=None, timeout: int = 15):
    """Fetch HTML and reject anti-bot challenge pages as source failures."""
    response = requests.get(url, headers=headers or HEADERS, timeout=timeout)
    response.raise_for_status()
    if _is_antibot_challenge(response.text):
        raise AntiBotChallenge(f"Anti-bot challenge returned by {url}")
    return response


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


def _split_reference(reference: str):
    """Return the English book and verse portion from a normalized reference."""
    match = _REFERENCE_PATTERN.fullmatch((reference or "").strip())
    if not match:
        return None
    return match.group("book"), re.sub(
        r"\s*[–—]\s*", "-", match.group("verses")
    ).replace(" ", "")


def _find_osis_reference(soup: BeautifulSoup) -> str:
    for element in soup.find_all(href=True):
        match = _OSIS_PATTERN.search(element.get("href", ""))
        if match:
            return match.group("osis").upper()
    return ""


def _extract_reference_and_data(html_text: str):
    """Extract the English reference, page data, source, and OSIS reference."""
    data = {}
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html_text,
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
                soup = BeautifulSoup(html_text, "html.parser")
                return reference, data, "__NEXT_DATA__", _find_osis_reference(soup)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            logging.warning("Could not parse Bible.com __NEXT_DATA__: %s", error)

    soup = BeautifulSoup(html_text, "html.parser")
    osis = _find_osis_reference(soup)

    if soup.title:
        reference = _find_reference(soup.title.get_text(" ", strip=True))
        if reference:
            return reference, data, "html-title", osis

    for element in soup.find_all(["a", "span", "p", "h1", "h2", "h3"]):
        reference = _find_reference(element.get_text(" ", strip=True))
        if reference:
            local_osis = ""
            if element.name == "a":
                match = _OSIS_PATTERN.search(element.get("href", ""))
                local_osis = match.group("osis").upper() if match else ""
            return reference, data, "visible-content", local_osis or osis

    reference = _find_reference(soup.get_text(" ", strip=True))
    if reference:
        return reference, data, "page-text", osis

    return "", data, "not-found", osis


def _daily_verse_urls(now=None):
    taipei_now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    day_of_year = taipei_now.timetuple().tm_yday
    return [
        f"https://www.bible.com/zh-TW/verse-of-the-day?day={day_of_year}",
        f"https://www.bible.com/verse-of-the-day?day={day_of_year}",
        "https://www.bible.com/zh-TW/verse-of-the-day",
    ]


def _fetch_bible_com_reference(now=None):
    """Fetch today's reference from Bible.com, rejecting challenge pages."""
    failures = []

    for url in _daily_verse_urls(now):
        try:
            response = _get_html(url)
            reference, data, source, osis_reference = _extract_reference_and_data(
                response.text
            )
            if reference:
                logging.info(
                    "Bible.com reference extracted via %s from %s: %s (osis=%s)",
                    source,
                    getattr(response, "url", url),
                    reference,
                    osis_reference or "not-found",
                )
                return reference, data, osis_reference, f"Bible.com/{source}"

            failures.append(f"{url}: reference not found")
        except (requests.RequestException, AntiBotChallenge) as error:
            failures.append(f"{url}: {type(error).__name__}: {error}")
            logging.warning("Bible.com reference request failed for %s: %s", url, error)

    raise ReferenceUnavailable("; ".join(failures))


def _bible_gateway_daily_url(now=None) -> str:
    taipei_now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    return (
        "https://www.biblegateway.com/reading-plans/verse-of-the-day/"
        f"{taipei_now.year:04d}/{taipei_now.month:02d}/{taipei_now.day:02d}"
    )


def _decode_json_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except (TypeError, ValueError, json.JSONDecodeError):
        return html.unescape(value or "")


def _fetch_bible_gateway_reference(now=None):
    """Fetch a date-addressable daily reference from Bible Gateway."""
    url = _bible_gateway_daily_url(now)
    response = _get_html(url)
    match = re.search(r'"ref_display"\s*:\s*"([^"]+)"', response.text)
    if not match:
        match = re.search(r'data-ref_display="([^"]+)"', response.text)
    if not match:
        raise ReferenceUnavailable("Bible Gateway reference was not found")

    reference = _find_reference(_decode_json_string(match.group(1)))
    if not reference:
        raise ReferenceUnavailable(
            f"Bible Gateway reference could not be parsed: {match.group(1)}"
        )

    logging.warning("Using Bible Gateway reference fallback: %s", reference)
    return reference, {}, "", "BibleGateway"


def _fetch_ourmanna_reference(now=None):
    """Fetch a last-resort daily reference from OurManna's JSON endpoint."""
    del now  # The provider owns the current-day calculation.
    url = "https://beta.ourmanna.com/api/v1/get/?format=json"
    response = requests.get(
        url,
        headers={"Accept": "application/json", "User-Agent": HEADERS["User-Agent"]},
        timeout=15,
    )
    response.raise_for_status()
    if _is_antibot_challenge(response.text):
        raise AntiBotChallenge(f"Anti-bot challenge returned by {url}")

    payload = response.json()
    raw_reference = payload.get("verse", {}).get("details", {}).get("reference", "")
    reference = _find_reference(raw_reference)
    if not reference:
        raise ReferenceUnavailable(
            f"OurManna reference could not be parsed: {raw_reference}"
        )

    logging.warning("Using OurManna reference fallback: %s", reference)
    return reference, {}, "", "OurManna"


def _fetch_daily_reference(now=None):
    """Fetch a reference using independent providers in priority order."""
    providers = (
        _fetch_bible_com_reference,
        _fetch_bible_gateway_reference,
        _fetch_ourmanna_reference,
    )
    failures = []

    for provider in providers:
        try:
            return provider(now)
        except (requests.RequestException, ScraperSourceError, ValueError) as error:
            failures.append(f"{provider.__name__}: {type(error).__name__}: {error}")
            logging.warning("Daily reference provider failed: %s", error)

    raise ReferenceUnavailable("; ".join(failures))


def _find_cunp_url(compare_html: str, compare_url: str) -> str:
    soup = BeautifulSoup(compare_html, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        label = link.get_text(" ", strip=True)
        if "CUNP" in href.upper() or "新標點和合本" in label or "和合本" in label:
            return urljoin(compare_url, href)

    match = _CUNP_LINK_PATTERN.search(compare_html)
    return urljoin(compare_url, match.group(0)) if match else ""


def _direct_cunp_url(osis_reference: str) -> str:
    """Build the YouVersion CUNP-神 URL using version id 46."""
    return f"https://www.bible.com/zh-TW/bible/46/{osis_reference}.CUNP-%E7%A5%9E"


def _has_chinese_text(value: str, minimum: int = 8) -> bool:
    return sum("\u4e00" <= char <= "\u9fff" for char in value) >= minimum


def _clean_cunp_candidate(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""

    if " - " in value and ("CUNP" in value or "和合本" in value):
        value = value.split(" - ", 1)[1]

    value = re.sub(r"^.*?CUNP(?:-神)?\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*\([^)]*新標點和合本[^)]*\)\s*", "", value)
    value = re.split(
        r"\s*(?:\|\s*YouVersion|分享|閱讀\s|聆聽\s|對照全部譯本)",
        value,
        maxsplit=1,
    )[0]
    value = re.sub(r"^\d+\s*", "", value).strip(" -|\n\t")
    return value if _has_chinese_text(value) else ""


def _extract_cunp_from_compare_page(compare_html: str) -> str:
    soup = BeautifulSoup(compare_html, "html.parser")
    page_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))

    for match in re.finditer(r"CUNP(?:-神)?", page_text, re.I):
        segment = page_text[match.end():]
        segment = re.sub(r"^\s*\([^)]*\)\s*", "", segment)
        segment = re.split(
            r"\s+(?:分享|閱讀|RCUV|CNV|CCB|和合本修訂版|新譯本|當代譯本)",
            segment,
            maxsplit=1,
        )[0]
        candidate = _clean_cunp_candidate(segment)
        if candidate:
            return candidate

    return ""


def _extract_cunp_text(verse_html: str) -> str:
    soup = BeautifulSoup(verse_html, "html.parser")

    fragments = []
    for element in soup.select("[data-usfm]"):
        text = element.get_text(" ", strip=True)
        text = re.sub(r"^\d+\s*", "", text)
        if text and text not in fragments:
            fragments.append(text)
    if fragments:
        return " ".join(fragments).strip()

    for attrs in (
        {"property": "og:description"},
        {"name": "description"},
        {"name": "twitter:description"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta:
            candidate = _clean_cunp_candidate(meta.get("content", ""))
            if candidate:
                return candidate

    if soup.title:
        candidate = _clean_cunp_candidate(soup.title.get_text(" ", strip=True))
        if candidate:
            return candidate

    for selector in (
        "[class*='ChapterContent_content']",
        "[class*='BibleReader']",
        "main",
    ):
        for element in soup.select(selector):
            candidate = _clean_cunp_candidate(element.get_text(" ", strip=True))
            if candidate:
                return candidate

    return ""


def _fetch_cunp_from_youversion(osis_reference: str) -> str:
    compare_url = f"https://www.bible.com/zh-TW/bible/compare/{osis_reference}"
    cunp_url = ""

    try:
        compare_response = _get_html(compare_url)

        compare_text = _extract_cunp_from_compare_page(compare_response.text)
        if compare_text:
            logging.info("Extracted CUNP verse directly from Bible.com comparison page.")
            return compare_text

        cunp_url = _find_cunp_url(compare_response.text, compare_response.url)
    except (requests.RequestException, ScraperSourceError) as error:
        logging.warning("Bible.com comparison page request failed: %s", error)

    if not cunp_url:
        cunp_url = _direct_cunp_url(osis_reference)
        logging.info("CUNP link absent on comparison page; using direct Bible.com CUNP URL.")

    verse_response = _get_html(cunp_url)
    verse_text = _extract_cunp_text(verse_response.text)
    if not verse_text:
        raise ValueError("CUNP verse text was empty on Bible.com")
    return verse_text


def _fetch_cuv_fallback(chi_book: str, verses_ref: str) -> str:
    """Fetch CUV text using bible-api.com's Traditional Chinese book names."""
    candidate_books = [chi_book]
    api_alias = _CUV_API_BOOK_ALIASES.get(chi_book)
    if api_alias and api_alias not in candidate_books:
        candidate_books.append(api_alias)

    failures = []
    for api_book in candidate_books:
        query = f"{api_book} {verses_ref}"
        api_url = f"https://bible-api.com/{quote(query)}?translation=cuv"
        try:
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            text = data.get("text", "").strip()
            if text:
                return text
            failures.append(f"{query}: empty response")
        except (requests.RequestException, ValueError) as error:
            failures.append(f"{query}: {type(error).__name__}: {error}")

    raise ValueError("; ".join(failures) or "Bible API returned no verse text")


def get_daily_verse(now=None):
    """Fetch today's reference, then fetch Chinese text with layered fallbacks."""
    try:
        ref_title, data, osis_reference, reference_source = _fetch_daily_reference(now)
    except ReferenceUnavailable as error:
        logging.error("All daily reference sources failed: %s", error)
        return None

    parsed_reference = _split_reference(ref_title)
    if not parsed_reference:
        logging.error("Could not parse reference format: %s", ref_title)
        return None

    eng_book, verses_ref = parsed_reference
    chi_book = book_mapping.get(eng_book, eng_book)
    logging.info("Using daily reference source: %s (%s)", reference_source, ref_title)

    verse_text = ""
    if osis_reference:
        try:
            verse_text = _fetch_cunp_from_youversion(osis_reference)
            logging.info("Fetched CUNP verse from Bible.com.")
        except (requests.RequestException, ScraperSourceError, ValueError) as error:
            logging.warning("Bible.com CUNP lookup failed; using CUV fallback: %s", error)

    if not verse_text:
        try:
            verse_text = _fetch_cuv_fallback(chi_book, verses_ref)
            logging.info("Fetched CUV verse from bible-api.com fallback.")
        except (requests.RequestException, ValueError) as error:
            logging.error("All Chinese verse sources failed: %s", error)
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

    return {"text": verse_text, "reference": formatted_ref, "image_url": image_url}


if __name__ == "__main__":
    result = get_daily_verse()
    print(result if result else "Failed to fetch data.")
