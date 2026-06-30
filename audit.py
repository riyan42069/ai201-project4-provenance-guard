import json
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit.jsonl")


def write_entry(entry):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def find_entry(content_id):
    if not os.path.exists(LOG_PATH):
        return None
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("content_id") == content_id:
                    return entry
            except json.JSONDecodeError:
                continue
    return None


def update_entry(content_id, updates):
    if not os.path.exists(LOG_PATH):
        return False
    lines = []
    found = False
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
                if entry.get("content_id") == content_id:
                    entry.update(updates)
                    found = True
                lines.append(json.dumps(entry))
            except json.JSONDecodeError:
                lines.append(stripped)
    if found:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return found


def read_log(limit=20):
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(entries))[:limit]
