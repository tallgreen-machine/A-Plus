import os
from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE", os.path.join(os.path.dirname(__file__), "..", "config", ".env")))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # or 'ollama'

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "trad")
DB_USER = os.getenv("DB_USER", "trad")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tradpassword")
