import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_required_setting(name):
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(f"{name} is missing. Check your .env file.")

    return value


BASE_URL = get_required_setting("BASE_URL").rstrip("/")
TEST_USERNAME = get_required_setting("TEST_USERNAME")
TEST_PASSWORD = get_required_setting("TEST_PASSWORD")

try:
    TIMEOUT = int(os.getenv("TIMEOUT", "20"))
except ValueError:
    raise ValueError("TIMEOUT must be a whole number.") from None

if TIMEOUT <= 0:
    raise ValueError("TIMEOUT must be greater than zero.")