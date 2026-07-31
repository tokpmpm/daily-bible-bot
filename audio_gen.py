import asyncio
import logging
import os
import time

import edge_tts
import requests

from config import (
    EDGE_TTS_MAX_ATTEMPTS,
    OPENAI_API_KEY,
    OPENAI_TTS_MAX_ATTEMPTS,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
    TTS_PITCH,
    TTS_RATE,
    TTS_STYLE_INSTRUCTIONS,
    TTS_VOICE,
    TTS_VOLUME,
)
from tts_normalizer import prepare_tts_text


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"


def _cleanup_temp_file(temp_path):
    """Remove a temporary TTS file without masking the original failure."""
    try:
        os.remove(temp_path)
    except FileNotFoundError:
        pass
    except OSError as cleanup_error:
        logging.error(
            "Failed to remove temporary TTS file %s: %s: %s",
            temp_path,
            type(cleanup_error).__name__,
            str(cleanup_error),
        )


def _remove_existing_output(output_path):
    """Ensure an old output cannot be mistaken for a successful new run."""
    try:
        os.remove(output_path)
    except FileNotFoundError:
        return True
    except OSError as error:
        logging.error(
            "Unable to remove existing audio output %s: %s: %s",
            output_path,
            type(error).__name__,
            str(error),
        )
        return False
    return True


def _validate_temp_file(temp_path):
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f"TTS provider did not create temporary file: {temp_path}")

    if os.path.getsize(temp_path) <= 0:
        raise ValueError(f"TTS provider created an empty temporary file: {temp_path}")


async def _generate_edge_audio(spoken_text, output_path):
    edge_temp_path = f"{output_path}.edge.tmp"
    _cleanup_temp_file(edge_temp_path)

    for attempt in range(1, EDGE_TTS_MAX_ATTEMPTS + 1):
        try:
            communicate = edge_tts.Communicate(
                text=spoken_text,
                voice=TTS_VOICE,
                rate=TTS_RATE,
                volume=TTS_VOLUME,
                pitch=TTS_PITCH,
            )
            await communicate.save(edge_temp_path)
            _validate_temp_file(edge_temp_path)
            os.replace(edge_temp_path, output_path)
            logging.info("TTS provider used: edge")
            return True
        except Exception as error:
            logging.warning(
                "Edge TTS attempt %d/%d failed (voice=%s, rate=%s, "
                "exception=%s, message=%s)",
                attempt,
                EDGE_TTS_MAX_ATTEMPTS,
                TTS_VOICE,
                TTS_RATE,
                type(error).__name__,
                str(error),
            )
            _cleanup_temp_file(edge_temp_path)

            if attempt < EDGE_TTS_MAX_ATTEMPTS:
                retry_delay = 2 ** attempt
                logging.info(
                    "Retrying Edge TTS in %d seconds after attempt %d/%d",
                    retry_delay,
                    attempt,
                    EDGE_TTS_MAX_ATTEMPTS,
                )
                await asyncio.sleep(retry_delay)

    logging.error("Edge TTS failed after initial attempt and two retries")
    logging.error("Switching to OpenAI TTS fallback")
    return False


def _log_openai_response_error(response):
    if response is None:
        return
    try:
        status_code = response.status_code
        response_text = response.text
    except Exception as error:
        logging.error(
            "OpenAI TTS response could not be read (%s: %s)",
            type(error).__name__,
            str(error),
        )
        return

    logging.error(
        "OpenAI TTS HTTP response status=%s; full error response: %s",
        status_code,
        response_text,
    )


def _generate_openai_audio(spoken_text, output_path):
    openai_temp_path = f"{output_path}.openai.tmp"
    _cleanup_temp_file(openai_temp_path)

    if not OPENAI_API_KEY:
        logging.error("OpenAI TTS fallback unavailable: OPENAI_API_KEY is not set.")
        return False

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    request_data = {
        "model": OPENAI_TTS_MODEL,
        "voice": OPENAI_TTS_VOICE,
        "input": spoken_text,
        "instructions": TTS_STYLE_INSTRUCTIONS,
        "response_format": "mp3",
    }

    for attempt in range(1, OPENAI_TTS_MAX_ATTEMPTS + 1):
        response = None
        try:
            response = requests.post(
                OPENAI_TTS_URL,
                headers=headers,
                json=request_data,
                timeout=120,
            )
            response.raise_for_status()

            with open(openai_temp_path, "wb") as audio_file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        audio_file.write(chunk)

            _validate_temp_file(openai_temp_path)
            os.replace(openai_temp_path, output_path)
            logging.info("TTS provider used: openai")
            return True
        except Exception as error:
            logging.warning(
                "OpenAI TTS attempt %d/%d failed (model=%s, voice=%s, "
                "exception=%s, message=%s)",
                attempt,
                OPENAI_TTS_MAX_ATTEMPTS,
                OPENAI_TTS_MODEL,
                OPENAI_TTS_VOICE,
                type(error).__name__,
                str(error),
            )
            _log_openai_response_error(response)
            _cleanup_temp_file(openai_temp_path)

            if attempt < OPENAI_TTS_MAX_ATTEMPTS:
                logging.info(
                    "Retrying OpenAI TTS in 2 seconds after attempt %d/%d",
                    attempt,
                    OPENAI_TTS_MAX_ATTEMPTS,
                )
                time.sleep(2)

    logging.error("OpenAI TTS failed after %d attempts", OPENAI_TTS_MAX_ATTEMPTS)
    return False


def generate_audio(text, output_path="daily_message.mp3"):
    """Generate audio with Edge TTS first and OpenAI TTS as a final fallback."""
    if not isinstance(text, str):
        logging.error("TTS input must be a string; received %s", type(text).__name__)
        return None

    spoken_text = prepare_tts_text(text)
    if spoken_text != text:
        logging.info("TTS pronunciation normalization applied")

    if not _remove_existing_output(output_path):
        return None

    _cleanup_temp_file(f"{output_path}.edge.tmp")
    _cleanup_temp_file(f"{output_path}.openai.tmp")

    edge_succeeded = asyncio.run(_generate_edge_audio(spoken_text, output_path))
    if edge_succeeded:
        return output_path

    openai_succeeded = _generate_openai_audio(spoken_text, output_path)
    if openai_succeeded:
        return output_path

    _cleanup_temp_file(f"{output_path}.edge.tmp")
    _cleanup_temp_file(f"{output_path}.openai.tmp")
    logging.error("Both Edge TTS and OpenAI TTS failed")
    return None


if __name__ == "__main__":
    text = """願祂在教會中，並在基督耶穌裡，得著榮耀，直到世世代代，永永遠遠。阿們。

我們因信重生，重新得力，在真理中行走。教會長老長久忍耐，以音樂敬拜，心中充滿喜樂。即使生命有重量，仍然仰望神。

以弗所書 3章20-21節。"""

    print("\n" + "=" * 60)
    print("🎤 TTS Test")
    print("=" * 60)
    print(f"Edge voice: {TTS_VOICE}")
    print(f"Edge rate: {TTS_RATE}")
    print(f"Edge volume: {TTS_VOLUME}")
    print(f"Edge pitch: {TTS_PITCH}")
    print(f"OpenAI model: {OPENAI_TTS_MODEL}")
    print(f"OpenAI voice: {OPENAI_TTS_VOICE}")
    print("=" * 60 + "\n")

    output = generate_audio(text)
    if output:
        print(f"✅ Audio generated: {output}")
    else:
        print("❌ Failed to generate audio.")
