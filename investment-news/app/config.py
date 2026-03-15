import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

# Timezone
KST = ZoneInfo("Asia/Seoul")

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_BATCH_MODEL = "claude-sonnet-4-6"

# DB
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "investment_news.db")
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

# App
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_BATCH_SIZE = 50
