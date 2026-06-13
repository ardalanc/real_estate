# config.py
import os

PAGE_SIZE = 5
ITEMS_PER_PAGE = 5
VISIT_ITEMS_PER_PAGE = 5


ADMIN_IDS = [715337548]


BOT_TOKEN = os.environ.get("BOT_TOKEN")

DB_NAME = "amlak"

DATABASE_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
}
