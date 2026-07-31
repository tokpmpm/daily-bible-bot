import asyncio
import logging
import os

import edge_tts

from config import TTS_PITCH, TTS_RATE, TTS_VOICE, TTS_VOLUME


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

MAX_ATTEMPTS = 3


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


async def _generate_audio_async(text, output_path):
    """Generate audio with Edge TTS and atomically publish the completed file."""
    temp_path = f"{output_path}.tmp"
    _cleanup_temp_file(temp_path)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=TTS_VOICE,
                rate=TTS_RATE,
                volume=TTS_VOLUME,
                pitch=TTS_PITCH,
            )
            await communicate.save(temp_path)

            if not os.path.exists(temp_path):
                raise FileNotFoundError(
                    f"Edge TTS did not create the temporary file: {temp_path}"
                )

            temp_size = os.path.getsize(temp_path)
            if temp_size <= 0:
                raise ValueError(
                    f"Edge TTS created an empty temporary file: {temp_path}"
                )

            os.replace(temp_path, output_path)
            logging.info(
                "Successfully generated audio at %s (voice=%s, rate=%s, volume=%s, pitch=%s)",
                output_path,
                TTS_VOICE,
                TTS_RATE,
                TTS_VOLUME,
                TTS_PITCH,
            )
            return output_path
        except Exception as error:
            logging.warning(
                "TTS attempt %d/%d failed (voice=%s, rate=%s, volume=%s, pitch=%s): %s: %s",
                attempt,
                MAX_ATTEMPTS,
                TTS_VOICE,
                TTS_RATE,
                TTS_VOLUME,
                TTS_PITCH,
                type(error).__name__,
                str(error),
            )
            _cleanup_temp_file(temp_path)

            if attempt < MAX_ATTEMPTS:
                retry_delay = 2 ** attempt
                logging.info(
                    "Retrying TTS in %d seconds after attempt %d/%d",
                    retry_delay,
                    attempt,
                    MAX_ATTEMPTS,
                )
                await asyncio.sleep(retry_delay)

    logging.error(
        "TTS failed after %d attempts (voice=%s, rate=%s, volume=%s, pitch=%s)",
        MAX_ATTEMPTS,
        TTS_VOICE,
        TTS_RATE,
        TTS_VOLUME,
        TTS_PITCH,
    )
    return None


def generate_audio(text, output_path="daily_message.mp3"):
    """
    Generate audio from text using Microsoft Edge TTS.

    Returns the output path on success, or None if all attempts fail.
    """
    return asyncio.run(_generate_audio_async(text, output_path))


if __name__ == "__main__":
    text = """生死在舌頭的權下，喜愛它的，必吃它所結的果子。箴言十八章二十一節。

這節經文提醒我們，言語的力量不容小覷。願我們所說的話，能成為帶來生命和光明的工具。阿們。"""

    print("\n" + "=" * 60)
    print("🎤 TTS Test")
    print("=" * 60)
    print(f"Voice: {TTS_VOICE}")
    print(f"Rate: {TTS_RATE}")
    print(f"Volume: {TTS_VOLUME}")
    print(f"Pitch: {TTS_PITCH}")
    print("=" * 60 + "\n")

    output = generate_audio(text)
    if output:
        print(f"✅ Audio generated: {output}")
    else:
        print("❌ Failed to generate audio.")
