import json
import uuid
from datetime import datetime

# ============================================================
# Records drone commands with timestamp and username.
# Logs saved to drone_audit.log in the project folder.
# ============================================================

LOG_PATH   = "drone_audit.log"
SESSION_ID = str(uuid.uuid4())[:8]   # Short unique ID per session


def log_command(username: str, command: str):
    """
    Append a command entry to the audit log.
    Only called when the command actually changes — no duplicates.

    Operator actions are recorded for accountability.
    """
    entry = {
        "session" : SESSION_ID,
        "time"    : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user"    : username,
        "command" : command,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")