import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import scraper


CURRENT_BIBLE_COM_HTML = """
<html>
  <head><title>Verse of the Day | Bible App</title></head>
  <body>
    <a href="/bible/111/1JN.4.16.NIV"><span>1 John 4:16 (NIV)</span></a>
  </body>
</html>
"""

COMPARE_HTML = """
<html><body>
  <a href="/zh-TW/bible/46/1JN.4.16.CUNP-%E7%A5%9E">新標點和合本，神版</a>
</body></html>
"""

COMPARE_WITH_TEXT_HTML = """
<html><body><main>
  <section>約翰一書 4:16 CUNP-神 (新標點和合本, 神版)
  神愛我們的心，我們也知道也信。 神就是愛；住在愛裏面的，就是住在神裏面，神也住在他裏面。
  分享 閱讀 約翰一書 4</section>
  <section>約翰一書 4:16 RCUV 和合本修訂版 其他譯文</section>
</main></body></html>
"""

COMPARE_WITHOUT_CUNP_HTML = """
<html><body><main>比較聖經譯本</main></body></html>
"""

CUNP_HTML = """
<html><body><main>
  <span data-usfm="1JN.4.16">16 神愛我們的心，我們也知道也信。</span>
</main></body></html>
"""

CUNP_META_HTML = """
<html><head>
  <title>約翰一書 4:16 (CUNP-神) - 神愛我們的心，我們也知道也信。 神就是愛；住在愛裏面的，就是住在神裏面 | YouVersion</title>
  <meta property="og:description" content="神愛我們的心，我們也知道也信。 神就是愛；住在愛裏面的，就是住在神裏面，神也住在他裏面。">
</head><body></body></html>
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
    def test_extracts_reference_and_osis(self):
        reference, data, source, osis = scraper._extract_reference_and_data(
            CURRENT_BIBLE_COM_HTML
        )
        self.assertEqual(reference, "1 John 4:16")
        self.assertEqual(data, {})
        self.assertEqual(source, "visible-content")
        self.assertEqual(osis, "1JN.4.16")

    def test_uses_taipei_day_of_year_and_prefers_chinese_page(self):
        now = datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        self.assertEqual(
            scraper._daily_verse_urls(now)[0],
            "https://www.bible.com/zh-TW/verse-of-the-day?day=219",
        )

    def test_finds_cunp_link_from_compare_page(self):
        url = scraper._find_cunp_url(
            COMPARE_HTML,
            "https://www.bible.com/zh-TW/bible/compare/1JN.4.16",
        )
        self.assertIn("/zh-TW/bible/46/1JN.4.16.CUNP-", url)

    def test_builds_direct_cunp_url(self):
        self.assertEqual(
            scraper._direct_cunp_url("1JN.4.16"),
            "https://www.bible.com/zh-TW/bible/46/1JN.4.16.CUNP-%E7%A5%9E",
        )

    def test_extracts_cunp_text(self):
        self.assertEqual(
            scraper._extract_cunp_text(CUNP_HTML),
            "神愛我們的心，我們也知道也信。",
        )

    def test_extracts_cunp_text_from_meta_description(self):
        self.assertEqual(
            scraper._extract_cunp_text(CUNP_META_HTML),
            "神愛我們的心，我們也知道也信。 神就是愛；住在愛裏面的，就是住在神裏面，神也住在他裏面。",
        )

    def test_extracts_cunp_text_from_compare_content(self):
        self.assertEqual(
            scraper._extract_cunp_from_compare_page(COMPARE_WITH_TEXT_HTML),
            "神愛我們的心，我們也知道也信。 神就是愛；住在愛裏面的，就是住在神裏面，神也住在他裏面。",
        )

    @patch("scraper.requests.get")
    def test_full_flow_prefers_bible_com_cunp(self, mock_get):
        daily = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/zh-TW/verse-of-the-day?day=219",
        )
        compare = FakeResponse(
            text=COMPARE_HTML,
            url="https://www.bible.com/zh-TW/bible/compare/1JN.4.16",
        )
        cunp = FakeResponse(
            text=CUNP_HTML,
            url="https://www.bible.com/zh-TW/bible/46/1JN.4.16.CUNP-%E7%A5%9E",
        )
        mock_get.side_effect = [daily, compare, cunp]

        now = datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        result = scraper.get_daily_verse(now=now)

        self.assertEqual(
            result,
            {
                "text": "神愛我們的心，我們也知道也信。",
                "reference": "約翰一書 4章16節",
                "image_url": None,
            },
        )
        self.assertEqual(len(mock_get.call_args_list), 3)
        self.assertIn("/bible/compare/1JN.4.16", mock_get.call_args_list[1].args[0])

    @patch("scraper.requests.get")
    def test_returns_compare_page_cunp_without_requesting_direct_page(self, mock_get):
        daily = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/zh-TW/verse-of-the-day?day=219",
        )
        compare = FakeResponse(
            text=COMPARE_WITH_TEXT_HTML,
            url="https://www.bible.com/zh-TW/bible/compare/1JN.4.16",
        )
        mock_get.side_effect = [daily, compare]

        result = scraper.get_daily_verse(
            now=datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        )

        self.assertEqual(result["reference"], "約翰一書 4章16節")
        self.assertIn("神就是愛", result["text"])
        self.assertEqual(len(mock_get.call_args_list), 2)

    @patch("scraper.requests.get")
    def test_uses_direct_cunp_url_when_compare_has_no_link(self, mock_get):
        daily = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/zh-TW/verse-of-the-day?day=219",
        )
        compare = FakeResponse(
            text=COMPARE_WITHOUT_CUNP_HTML,
            url="https://www.bible.com/zh-TW/bible/compare/1JN.4.16",
        )
        cunp = FakeResponse(
            text=CUNP_META_HTML,
            url="https://www.bible.com/zh-TW/bible/46/1JN.4.16.CUNP-%E7%A5%9E",
        )
        mock_get.side_effect = [daily, compare, cunp]

        result = scraper.get_daily_verse(
            now=datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        )

        self.assertEqual(result["reference"], "約翰一書 4章16節")
        self.assertIn("神就是愛", result["text"])
        direct_url = mock_get.call_args_list[2].args[0]
        self.assertEqual(
            direct_url,
            "https://www.bible.com/zh-TW/bible/46/1JN.4.16.CUNP-%E7%A5%9E",
        )

    @patch("scraper.requests.get")
    def test_falls_back_to_english_api_query_when_all_cunp_requests_fail(self, mock_get):
        daily = FakeResponse(
            text=CURRENT_BIBLE_COM_HTML,
            url="https://www.bible.com/zh-TW/verse-of-the-day?day=219",
        )
        compare_failure = FakeResponse(status=503)
        direct_failure = FakeResponse(status=503)
        api = FakeResponse(
            json_data={"text": "神愛我們的心，我們也知道也信。"},
            url="https://bible-api.com/1%20John%204%3A16?translation=cuv",
        )
        api.headers = {"Content-Type": "application/json"}
        mock_get.side_effect = [daily, compare_failure, direct_failure, api]

        result = scraper.get_daily_verse(
            now=datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        )

        self.assertEqual(result["reference"], "約翰一書 4章16節")
        fallback_url = mock_get.call_args_list[3].args[0]
        self.assertIn("1%20John%204%3A16", fallback_url)
        self.assertNotIn("%E7%B4%84%E7%BF%B0", fallback_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
