import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional for tests
    pass

# TODO(team): confirm the GPT model choice (cost, latency, quality) with the teaching partner.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
