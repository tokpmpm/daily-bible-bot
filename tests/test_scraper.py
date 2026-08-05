import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import scraper


CURRENT_BIBLE_COM_HTML = """
<!doctype html>
<html>
  <head><title>Verse of the Day | Bible App</title></head>
  <body>
    <main>
      <h1>Verse of the Day</h1>
      <p>August 5, 2026</p>
      <a href="/bible/111/LUK.16.10.NIV">
        <span>Luke 16:10 (NIV)</span>
      </a>
      <section>
        <a href="/bible/111/JAS.3.13.NIV">James 3:13 (NIV)</a>
      </section>
    </main>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, *, text="", json_data=None, url="https://example.test", status=200):
        self.text = text
        self._json_data = json_data
        self.url = url
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise scraper.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON")
        return self._json_data


class ScraperTests(unittest.TestCase):
    def test_extracts_reference_from_current_visible_content(self):
        reference, data, source = scraper._extract_reference_and_data(CURRENT_BIBLE_COM_HTML)
        self.assertEqual(reference, "Luke 16:10")
        self.assertEqual(data, {})
        self.assertEqual(source, "visible-content")

    def test_keeps_legacy_next_data_compatibility(self):
        html = """
        <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"referenceTitle":{"title":"Matthew 9:37-38"}}}}
        </script>
        """
        reference, _, source = scraper._extract_reference_and_data(html)
        self.assertEqual(reference, "Matthew 9:37-38")
        self.assertEqual(source, "__NEXT_DATA__")

    def test_uses_taipei_day_of_year(self):
        now = datetime(2026, 8, 5, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        self.assertEqual(
            scraper._daily_verse_urls(now)[0],
            "https://www.bible.com/verse-of-the-day?day=217",
        )

    @patch("scraper.requests.get")
    def test_full_flow_returns_traditional_chinese_reference(self, mock_get):
        bible_page = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/verse-of-the-day?day=217",
        )
        bible_api = FakeResponse(
            json_data={"text": "測試經文內容"},
            url="https://bible-api.com/test",
        )
        bible_api.headers = {"Content-Type": "application/json"}
        mock_get.side_effect = [bible_page, bible_api]

        now = datetime(2026, 8, 5, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        result = scraper.get_daily_verse(now=now)

        self.assertEqual(
            result,
            {
                "text": "測試經文內容",
                "reference": "路加福音 16章10節",
                "image_url": None,
            },
        )
        self.assertEqual(
            mock_get.call_args_list[0].args[0],
            "https://www.bible.com/verse-of-the-day?day=217",
        )
        self.assertIn("translation=cuv", mock_get.call_args_list[1].args[0])

    def test_parses_multiple_current_reference_formats(self):
        cases = {
            "1 John 4:16 (NIV)": "1 John 4:16",
            "Psalms 34:19 (NIV)": "Psalms 34:19",
            "Ephesians 3:20-21 (NIV)": "Ephesians 3:20-21",
            "1 Corinthians 13:4 (NIV)": "1 Corinthians 13:4",
        }
        for source_text, expected in cases.items():
            with self.subTest(source_text=source_text):
                self.assertEqual(scraper._find_reference(source_text), expected)

    @patch("scraper.requests.get")
    def test_tries_localized_fallback_when_primary_page_has_no_reference(self, mock_get):
        empty_page = FakeResponse(
            text="<html><head><title>Verse of the Day</title></head><body></body></html>",
            url="https://www.bible.com/verse-of-the-day?day=217",
        )
        localized_page = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/zh-TW/verse-of-the-day?day=217",
        )
        bible_api = FakeResponse(
            json_data={"text": "測試經文內容"},
            url="https://bible-api.com/test",
        )
        bible_api.headers = {"Content-Type": "application/json"}
        mock_get.side_effect = [empty_page, localized_page, bible_api]

        now = datetime(2026, 8, 5, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        result = scraper.get_daily_verse(now=now)

        self.assertEqual(result["reference"], "路加福音 16章10節")
        self.assertEqual(len(mock_get.call_args_list), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
