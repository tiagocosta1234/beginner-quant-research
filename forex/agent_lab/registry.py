"""Append-only registry of every hypothesis the agent tests. The validation counter never resets: it sets the significance bar (evaluate.z_bar)."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = HERE / "registry.jsonl"
PROMOTED = HERE / "promoted"


def rows() -> list[dict]:
    if not REG.exists():
        return []
    return [json.loads(l) for l in REG.read_text(encoding="utf-8").splitlines() if l.strip()]


def n_validations() -> int:
    return sum(1 for r in rows() if r.get("validated"))


def code_hash(code: str) -> str:
    return hashlib.sha256(" ".join(code.split()).encode()).hexdigest()[:12]


def seen(code: str) -> bool:
    h = code_hash(code)
    return any(r.get("hash") == h for r in rows())


def log(entry: dict):
    entry["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(REG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def promote(entry: dict, code: str):
    PROMOTED.mkdir(exist_ok=True)
    (PROMOTED / f"{entry['hash']}.py").write_text(code, encoding="utf-8")
    (PROMOTED / f"{entry['hash']}.json").write_text(json.dumps(entry, indent=1, default=str), encoding="utf-8")
