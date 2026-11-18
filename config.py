from __future__ import annotations
import json, os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def load_json_config(path: str = "config/commodities.json") -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as f:
        return json.load(f)

def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)

def data_dir() -> Path:
    p = ROOT / (env("DATA_DIR", "data") or "data")
    p.mkdir(parents=True, exist_ok=True)
    return p
