import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional for tests
    pass

# TODO(team): confirm the GPT model choice (cost, latency, quality) with the teaching partner.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MAX_TURNS = int(os.getenv("MAX_TURNS", "20"))  # customer messages per session before handing off
MIN_CONFIDENCE = 0.6  # below this the intent gate asks a clarifying question
MAX_UNCLEAR_TURNS = 2  # consecutive unclear messages before handing off
HISTORY_TURNS = 6  # recent messages sent to the intent gate


def llm_enabled() -> bool:
    """Tests and offline runs set SUPPORT_AGENT_OFFLINE=1 to use the keyword fallback instead of the LLM."""
    return os.getenv("SUPPORT_AGENT_OFFLINE") != "1" and bool(os.getenv("OPENAI_API_KEY"))
