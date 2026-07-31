import os
import tempfile
import unittest
from unittest.mock import patch

import audio_gen


class FakeEdgeCommunicate:
    def __init__(self, calls, payload=b"edge-audio", error=None, partial=False):
        self.calls = calls
        self.payload = payload
        self.error = error
        self.partial = partial

    async def save(self, path):
        if self.partial:
            with open(path, "wb") as audio_file:
                audio_file.write(b"partial")
        if self.error:
            raise self.error
        with open(path, "wb") as audio_file:
            audio_file.write(self.payload)


class FakeOpenAIResponse:
    def __init__(self, payload=b"openai-audio", status_code=200, error=None):
        self.payload = payload
        self.status_code = status_code
        self.text = "{\"error\":\"test response\"}" if error else "{\"ok\":true}"
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def iter_content(self, chunk_size=1024):
        yield self.payload


class TestAudioGeneration(unittest.TestCase):
    def setUp(self):
        self.openai_key_patcher = patch.object(audio_gen, "OPENAI_API_KEY", "test-openai-key")
        self.openai_key_patcher.start()
        self.addCleanup(self.openai_key_patcher.stop)
        self.async_sleeps = []
        self.sync_sleeps = []

        async def fake_async_sleep(seconds):
            self.async_sleeps.append(seconds)

        self.fake_async_sleep = fake_async_sleep

    def _edge_constructor_from_sequence(self, sequence, calls):
        def constructor(**kwargs):
            calls.append(kwargs)
            item = sequence.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        return constructor

    def test_edge_first_attempt_success_does_not_call_openai(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            calls = []
            sequence = [FakeEdgeCommunicate(calls)]
            constructor = self._edge_constructor_from_sequence(sequence, calls)

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(audio_gen, "_generate_openai_audio") as openai:
                result = audio_gen.generate_audio("得著榮耀", output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["text"], "得着榮耀")
            self.assertEqual(calls[0]["voice"], "zh-TW-HsiaoChenNeural")
            self.assertEqual(calls[0]["rate"], "-5%")
            self.assertEqual(calls[0]["volume"], "+0%")
            self.assertEqual(calls[0]["pitch"], "+0Hz")
            self.assertNotIn(audio_gen.TTS_STYLE_INSTRUCTIONS, calls[0]["text"])
            openai.assert_not_called()
            self.assertTrue(os.path.exists(output_path))

    def test_edge_first_failure_second_success_sleeps_two_seconds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            calls = []
            sequence = [RuntimeError("first edge failure"), FakeEdgeCommunicate(calls)]
            constructor = self._edge_constructor_from_sequence(sequence, calls)

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(audio_gen, "_generate_openai_audio") as openai:
                result = audio_gen.generate_audio("普通文字", output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.async_sleeps, [2])
            openai.assert_not_called()

    def test_edge_first_two_failures_third_success_sleeps_two_and_four(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            calls = []
            sequence = [
                RuntimeError("first edge failure"),
                RuntimeError("second edge failure"),
                FakeEdgeCommunicate(calls),
            ]
            constructor = self._edge_constructor_from_sequence(sequence, calls)

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(audio_gen, "_generate_openai_audio") as openai:
                result = audio_gen.generate_audio("普通文字", output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(len(calls), 3)
            self.assertEqual(self.async_sleeps, [2, 4])
            openai.assert_not_called()

    def test_three_edge_failures_start_openai_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            edge_calls = []
            sequence = [RuntimeError("edge failure") for _ in range(3)]
            constructor = self._edge_constructor_from_sequence(sequence, edge_calls)

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(audio_gen, "_generate_openai_audio", return_value=True) as openai:
                result = audio_gen.generate_audio("普通文字", output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(len(edge_calls), 3)
            self.assertEqual(self.async_sleeps, [2, 4])
            openai.assert_called_once()

    def test_edge_failure_openai_success_uses_same_spoken_text_and_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            edge_calls = []
            sequence = [RuntimeError("edge failure") for _ in range(3)]
            constructor = self._edge_constructor_from_sequence(sequence, edge_calls)
            response = FakeOpenAIResponse()
            original_text = "永永遠遠，得著榮耀。以弗所書 3章20-21節"
            spoken_text = "顒永遠遠，得着榮耀。以弗所書 三章二十到二十一節"

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(audio_gen, "prepare_tts_text", return_value=spoken_text) as normalize, \
                 patch.object(audio_gen.requests, "post", return_value=response) as post, \
                 patch.object(audio_gen.time, "sleep", side_effect=self.sync_sleeps.append):
                result = audio_gen.generate_audio(original_text, output_path)

            self.assertEqual(result, output_path)
            normalize.assert_called_once_with(original_text)
            post.assert_called_once()
            _, kwargs = post.call_args
            self.assertEqual(
                kwargs["json"],
                {
                    "model": "gpt-4o-mini-tts",
                    "voice": "nova",
                    "input": spoken_text,
                    "instructions": audio_gen.TTS_STYLE_INSTRUCTIONS,
                    "response_format": "mp3",
                },
            )
            self.assertEqual(self.async_sleeps, [2, 4])
            self.assertEqual(self.sync_sleeps, [])
            with open(output_path, "rb") as audio_file:
                self.assertEqual(audio_file.read(), b"openai-audio")
            self.assertFalse(os.path.exists(f"{output_path}.edge.tmp"))
            self.assertFalse(os.path.exists(f"{output_path}.openai.tmp"))

    def test_openai_retry_waits_two_seconds_and_can_succeed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            sequence = [RuntimeError("edge failure") for _ in range(3)]
            constructor = self._edge_constructor_from_sequence(sequence, [])
            response_failure = FakeOpenAIResponse(
                status_code=500, error=RuntimeError("openai temporary failure")
            )
            response_success = FakeOpenAIResponse()

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(
                     audio_gen.requests,
                     "post",
                     side_effect=[response_failure, response_success],
                 ) as post, \
                 patch.object(audio_gen.time, "sleep", side_effect=self.sync_sleeps.append):
                result = audio_gen.generate_audio("普通文字", output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(post.call_count, 2)
            self.assertEqual(self.sync_sleeps, [2])

    def test_both_providers_fail_remove_old_output_and_all_temp_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "daily_message.mp3")
            with open(output_path, "wb") as audio_file:
                audio_file.write(b"old audio that must not survive")
            with open(f"{output_path}.edge.tmp", "wb") as temp_file:
                temp_file.write(b"old edge temp")
            with open(f"{output_path}.openai.tmp", "wb") as temp_file:
                temp_file.write(b"old openai temp")

            sequence = [RuntimeError("edge failure") for _ in range(3)]
            constructor = self._edge_constructor_from_sequence(sequence, [])
            openai_response = FakeOpenAIResponse(
                status_code=500, error=RuntimeError("openai failure")
            )

            with patch.object(audio_gen.edge_tts, "Communicate", side_effect=constructor), \
                 patch.object(audio_gen.asyncio, "sleep", side_effect=self.fake_async_sleep), \
                 patch.object(
                     audio_gen.requests,
                     "post",
                     return_value=openai_response,
                 ), \
                 patch.object(audio_gen.time, "sleep", side_effect=self.sync_sleeps.append):
                result = audio_gen.generate_audio("普通文字", output_path)

            self.assertIsNone(result)
            self.assertEqual(self.async_sleeps, [2, 4])
            self.assertEqual(self.sync_sleeps, [2, 2])
            self.assertFalse(os.path.exists(output_path))
            self.assertFalse(os.path.exists(f"{output_path}.edge.tmp"))
            self.assertFalse(os.path.exists(f"{output_path}.openai.tmp"))


if __name__ == "__main__":
    unittest.main()
