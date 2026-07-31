"""Prepare a private, audio-only version of daily Bible text for TTS."""

import re


# These are phrase-level pronunciation proxies carried forward from the
# historical OpenAI TTS instructions. They must never be applied to user-facing
# text, database fields, podcast metadata, or logs.
PRONUNCIATION_REPLACEMENTS = (
    # 顒 is an audio-only pronunciation proxy for a second-tone first 永.
    ("永永遠遠", "顒永遠遠"),
    ("得著", "得着"),
    ("重新", "崇新"),
    ("重生", "崇生"),
    ("重量", "仲量"),
    ("長老", "掌老"),
    ("長久", "常久"),
    ("行走", "形走"),
    ("音樂", "音悅"),
    ("喜樂", "喜勒"),
)

_CHINESE_DIGITS = "零一二三四五六七八九"
_CHAPTER_RANGE_PATTERN = re.compile(
    r"(\d+)\s*章\s*(\d+)\s*[-–—－~～至到]\s*(\d+)\s*節"
)
_SINGLE_VERSE_PATTERN = re.compile(r"(\d+)\s*章\s*(\d+)\s*節")


def _under_one_hundred(number):
    if number < 10:
        return _CHINESE_DIGITS[number]
    if number < 20:
        return "十" if number == 10 else "十" + _CHINESE_DIGITS[number - 10]

    tens, ones = divmod(number, 10)
    return f"{_CHINESE_DIGITS[tens]}十" + (_CHINESE_DIGITS[ones] if ones else "")


def _integer_to_chinese(number):
    """Convert integers from 0 through 199 to traditional Chinese numerals."""
    if not 0 <= number <= 199:
        raise ValueError("chapter and verse numbers must be between 0 and 199")
    if number < 100:
        return _under_one_hundred(number)

    remainder = number - 100
    if remainder == 0:
        return "一百"
    if remainder < 10:
        return f"一百零{_CHINESE_DIGITS[remainder]}"
    if remainder < 20:
        return "一百一十" if remainder == 10 else "一百一十" + _CHINESE_DIGITS[remainder - 10]
    return f"一百{_under_one_hundred(remainder)}"


def _replace_range(match):
    try:
        chapter = _integer_to_chinese(int(match.group(1)))
        start_verse = _integer_to_chinese(int(match.group(2)))
        end_verse = _integer_to_chinese(int(match.group(3)))
    except ValueError:
        return match.group(0)
    return f"{chapter}章{start_verse}到{end_verse}節"


def _replace_single_verse(match):
    try:
        chapter = _integer_to_chinese(int(match.group(1)))
        verse = _integer_to_chinese(int(match.group(2)))
    except ValueError:
        return match.group(0)
    return f"{chapter}章{verse}節"


def prepare_tts_text(text: str) -> str:
    """Return a TTS-only text copy while leaving the source text untouched."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")

    normalized = _CHAPTER_RANGE_PATTERN.sub(_replace_range, text)
    normalized = _SINGLE_VERSE_PATTERN.sub(_replace_single_verse, normalized)

    # Longer phrases are intentionally listed before shorter overlapping ones.
    for source, proxy in PRONUNCIATION_REPLACEMENTS:
        normalized = normalized.replace(source, proxy)

    return normalized
