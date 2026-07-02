import json
import os
import time

from . import config


def log_judgment(record: dict) -> None:
    """Append one judgment record to logs/judgments.jsonl (JSON Lines)."""
    entry = {"logged_at": time.time(), **record}
    os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
    with open(config.LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
