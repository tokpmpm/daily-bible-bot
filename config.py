import logging
import os


logger = logging.getLogger(__name__)


def load_env_manual():
    """
    Manually loads environment variables from a .env file.
    """
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ[key.strip()] = value

load_env_manual()


def positive_int_env(name, default):
    """Read a positive integer environment variable without breaking imports."""
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; using default %d.", name, raw_value, default)
        return default

    if value <= 0:
        logger.warning("Invalid %s=%r; using default %d.", name, raw_value, default)
        return default

    return value


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "nova")
TTS_STYLE_INSTRUCTIONS = (
    "請使用自然、溫暖的台灣華語女聲朗讀。"
    "語速穩定、清楚，像每日靈修 Podcast 的旁白。"
    "經文莊重但不要像新聞播報，解經親切自然，禱告真摯柔和。"
    "忠實朗讀內容，不可摘要、改寫、加字或省略。"
    "注意中文破音字、聖經用語與數字段落的自然停頓。"
)
RUN_MODE = os.getenv("RUN_MODE", "production").strip().lower()
TTS_VOICE = os.getenv("TTS_VOICE", "zh-TW-HsiaoChenNeural")
TTS_RATE = os.getenv("TTS_RATE", "-5%")
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")
EDGE_TTS_MAX_ATTEMPTS = positive_int_env("EDGE_TTS_MAX_ATTEMPTS", 3)
OPENAI_TTS_MAX_ATTEMPTS = positive_int_env("OPENAI_TTS_MAX_ATTEMPTS", 3)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# Telegram Bot API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_TEST_CHAT_ID = os.getenv("TELEGRAM_TEST_CHAT_ID", "").strip()
TELEGRAM_CHAT_IDS = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Web Push VAPID Keys
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")

# Cloudflare Worker audio upload
AUDIO_UPLOAD_URL = os.getenv("AUDIO_UPLOAD_URL", "")
AUDIO_UPLOAD_SECRET = os.getenv("AUDIO_UPLOAD_SECRET", "")
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL", "")

# Testing
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set.")
if not LINE_CHANNEL_ACCESS_TOKEN:
    print("Warning: LINE_CHANNEL_ACCESS_TOKEN is not set.")
if not LINE_CHANNEL_SECRET:
    print("Warning: LINE_CHANNEL_SECRET is not set.")
if not TELEGRAM_BOT_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN is not set.")
if not TELEGRAM_CHAT_IDS:
    print("Warning: TELEGRAM_CHAT_IDS is not set.")
if not SUPABASE_URL:
    print("Info: SUPABASE_URL is not set. Web features disabled.")
