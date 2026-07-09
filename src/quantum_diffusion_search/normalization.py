"""Deterministic metadata normalization utilities."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
    return text or None


def normalize_doi(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.strip().lower()
    text = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    text = text.strip(" .;,\t\n\r")
    text = re.sub(r"\s+", "", text)
    if not text.startswith("10."):
        return None
    return text


def normalize_title(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_authors(authors: Any) -> list[str]:
    if authors is None:
        return []
    if isinstance(authors, str):
        parts = [p.strip() for p in re.split(r";|,\s*(?=[A-Z][^,]+(?:$|,))", authors) if p.strip()]
        return [clean_text(p) or "" for p in parts if clean_text(p)]
    if isinstance(authors, list):
        out: list[str] = []
        for item in authors:
            if isinstance(item, dict):
                name = item.get("name") or " ".join(x for x in [item.get("given"), item.get("family")] if x)
            else:
                name = getattr(item, "name", str(item))
            cleaned = clean_text(name)
            if cleaned:
                out.append(cleaned)
        return out
    cleaned = clean_text(authors)
    return [cleaned] if cleaned else []


def extract_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def strip_arxiv_version(arxiv_id: str | None) -> str | None:
    if not arxiv_id:
        return None
    return re.sub(r"v\d+$", "", str(arxiv_id).strip())


def extract_arxiv_id(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", text)
    if match:
        return strip_arxiv_version(match.group(1))
    old = re.search(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", text, re.I)
    return strip_arxiv_version(old.group(1)) if old else None


def crossref_list(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        vals = []
        for item in value:
            if isinstance(item, list):
                vals.extend(str(x) for x in item)
            elif isinstance(item, dict):
                vals.append(str(item))
            else:
                vals.append(str(item))
        return clean_text("; ".join(vals))
    return clean_text(value)


def parse_crossref_date(parts: Any) -> str | None:
    try:
        date_parts = parts.get("date-parts", [[]])[0] if isinstance(parts, dict) else parts[0]
    except (KeyError, IndexError, TypeError):
        return None
    if not date_parts:
        return None
    year = int(date_parts[0])
    month = int(date_parts[1]) if len(date_parts) > 1 else 1
    day = int(date_parts[2]) if len(date_parts) > 2 else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return f"{year:04d}-01-01"


def doi_from_text(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
    return normalize_doi(match.group(0)) if match else None
