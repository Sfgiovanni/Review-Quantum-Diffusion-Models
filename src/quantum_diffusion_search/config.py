"""Configuration loading and run-id helpers."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_stamp() -> str:
    return utc_now().strftime("%Y-%m-%dT%H%M%SZ")


def new_run_id() -> str:
    return f"{utc_stamp()}_{uuid.uuid4().hex[:7]}"


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Configuration YAML must contain a mapping.")
    return cfg


def resolve_config(config: dict[str, Any], run_date: date | None = None) -> dict[str, Any]:
    resolved = copy.deepcopy(config)
    date_range = resolved.setdefault("date_range", {})
    if date_range.get("until_pub_date") is None:
        date_range["until_pub_date"] = (run_date or utc_now().date()).isoformat()
    return resolved


def dump_yaml(data: dict[str, Any], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def stable_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
