import os
import unittest
from unittest.mock import patch

from config import positive_int_env


class TestConfig(unittest.TestCase):
    def test_positive_int_env_accepts_positive_integer(self):
        with patch.dict(os.environ, {"TEST_ATTEMPTS": "4"}):
            self.assertEqual(positive_int_env("TEST_ATTEMPTS", 3), 4)

    def test_positive_int_env_falls_back_for_invalid_values(self):
        for value in ("", "0", "-1", "not-an-int"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"TEST_ATTEMPTS": value}
            ):
                self.assertEqual(positive_int_env("TEST_ATTEMPTS", 3), 3)

    def test_positive_int_env_uses_default_when_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_ATTEMPTS", None)
            self.assertEqual(positive_int_env("TEST_ATTEMPTS", 3), 3)


if __name__ == "__main__":
    unittest.main()
