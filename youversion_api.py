import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://api.youversion.com/v1"
CUNP_VERSION_ID = 46


def _headers():
    app_key = os.environ.get("YOUVERSION_APP_KEY")
    if not app_key:
        raise RuntimeError("YOUVERSION_APP_KEY is not configured")
    return {"X-YVP-App-Key": app_key, "Accept": "application/json"}


def _day_of_year(now=None):
    taipei_now = now or datetime.now(ZoneInfo("Asia/Taipei"))
    return taipei_now.timetuple().tm_yday


def get_daily_verse(now=None):
    day = _day_of_year(now)
    headers = _headers()

    votd_response = requests.get(
        f"{API_BASE}/verse_of_the_days/{day}",
        headers=headers,
        timeout=20,
    )
    votd_response.raise_for_status()
    votd = votd_response.json()
    passage_id = votd.get("passage_id", "").strip()
    if not passage_id:
        raise ValueError(f"YouVersion VOTD response has no passage_id: {votd}")

    passage_response = requests.get(
        f"{API_BASE}/bibles/{CUNP_VERSION_ID}/passages/{passage_id}",
        headers=headers,
        timeout=20,
    )
    passage_response.raise_for_status()
    passage = passage_response.json()
    text = passage.get("content", "").strip()
    reference = passage.get("reference", "").strip()
    if not text or not reference:
        raise ValueError(f"YouVersion passage response is incomplete: {passage}")

    logging.info(
        "YouVersion API VOTD: day=%s passage=%s reference=%s text_length=%s",
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
