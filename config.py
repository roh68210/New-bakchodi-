import os

API_ID = int(os.environ.get("API_ID", "29719806"))
API_HASH = os.environ.get("API_HASH", "c8e87805739aa77bd5bd4076148a9a66")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "1394117837"))
SUDO_USERS = list(map(int, os.environ.get("SUDO_USERS", "").split())) if os.environ.get("SUDO_USERS") else []
