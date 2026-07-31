import unittest

from tts_normalizer import prepare_tts_text


class TestTtsNormalizer(unittest.TestCase):
    def test_new_pronunciation_proxies(self):
        self.assertEqual(prepare_tts_text("得著榮耀"), "得着榮耀")
        self.assertEqual(prepare_tts_text("直到得著榮耀"), "直到得着榮耀")
        self.assertEqual(prepare_tts_text("永永遠遠"), "顒永遠遠")

    def test_protected_著_phrases_are_not_changed(self):
        self.assertEqual(prepare_tts_text("這是一部著作"), "這是一部著作")
        self.assertEqual(prepare_tts_text("內容非常顯著"), "內容非常顯著")
        self.assertEqual(prepare_tts_text("他是一位著名作者"), "他是一位著名作者")

    def test_historical_pronunciation_proxies_are_preserved(self):
        self.assertEqual(prepare_tts_text("重新"), "崇新")
        self.assertEqual(prepare_tts_text("重生"), "崇生")
        self.assertEqual(prepare_tts_text("重量"), "仲量")
        self.assertEqual(prepare_tts_text("長老"), "掌老")
        self.assertEqual(prepare_tts_text("長久"), "常久")
        self.assertEqual(prepare_tts_text("行走"), "形走")
        self.assertEqual(prepare_tts_text("音樂"), "音悅")
        self.assertEqual(prepare_tts_text("喜樂"), "喜勒")

    def test_chapter_range_separators(self):
        source_prefix = "以弗所書 "
        for separator in ("-", "–", "—", "－", "~", "～", "至", "到"):
            with self.subTest(separator=separator):
                self.assertEqual(
                    prepare_tts_text(f"{source_prefix}3章20{separator}21節"),
                    "以弗所書 三章二十到二十一節",
                )

    def test_single_verse_and_integer_conversion(self):
        self.assertEqual(prepare_tts_text("以弗所書 3章20節"), "以弗所書 三章二十節")
        self.assertEqual(prepare_tts_text("0章0節"), "零章零節")
        self.assertEqual(prepare_tts_text("1章1節"), "一章一節")
        self.assertEqual(prepare_tts_text("1章10節"), "一章十節")
        self.assertEqual(prepare_tts_text("1章11節"), "一章十一節")
        self.assertEqual(prepare_tts_text("1章99節"), "一章九十九節")
        self.assertEqual(prepare_tts_text("100章101節"), "一百章一百零一節")
        self.assertEqual(prepare_tts_text("100章119節"), "一百章一百一十九節")
        self.assertEqual(prepare_tts_text("100章150節"), "一百章一百五十節")
        self.assertEqual(prepare_tts_text("100章199節"), "一百章一百九十九節")

    def test_dates_and_unmatched_text_are_preserved(self):
        ordinary_text = "2026-07-31，這是一段沒有發音規則的普通文字。"
        self.assertEqual(prepare_tts_text(ordinary_text), ordinary_text)

    def test_multiple_rules_and_source_immutability(self):
        source = "得著榮耀，永永遠遠，重新重生重量長老長久行走音樂喜樂。"
        original_copy = source[:]
        normalized = prepare_tts_text(source)
        self.assertEqual(source, original_copy)
        self.assertIn("得着榮耀", normalized)
        self.assertIn("顒永遠遠", normalized)
        self.assertIn("崇新崇生仲量掌老常久形走音悅喜勒", normalized)

    def test_non_string_input_is_explicitly_rejected(self):
        with self.assertRaises(TypeError):
            prepare_tts_text(None)
        with self.assertRaises(TypeError):
            prepare_tts_text(123)


if __name__ == "__main__":
    unittest.main()
