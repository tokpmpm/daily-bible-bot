import logging

import scraper
from youversion_api import get_daily_verse as get_daily_verse_from_youversion


# bot.py imports scraper.get_daily_verse directly, so install the API-backed
# implementation before importing bot. This keeps the existing bot pipeline intact.
scraper.get_daily_verse = get_daily_verse_from_youversion

import bot  # noqa: E402


if __name__ == "__main__":
    success = bot.run_daily_task()
    if not success:
        logging.error("Daily task failed")
        raise SystemExit(1)
