# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # Get from BotFather

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) # Set if your Redis requires auth

# --- Bot Settings ---
# No specific settings needed for now, could add admin IDs later if needed