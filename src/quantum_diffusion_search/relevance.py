"""Deterministic relevance scoring."""

from __future__ import annotations

import re
from typing import Any


def score_record(record: dict[str, Any], relevance_cfg: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(record.get(k) or "") for k in ["title", "abstract", "subjects", "categories", "container_title"]
    ).lower()
    score = 0
    positive: list[str] = []
    negative: list[str] = []
    for term, weight in relevance_cfg.get("base_terms", {}).items():
        if term.lower() in text:
            score += int(weight)
            positive.append(f"{term}:{weight}")
    for pattern, weight in relevance_cfg.get("positive_patterns", {}).items():
        if re.search(pattern, text, flags=re.I):
            score += int(weight)
            positive.append(f"{pattern}:{weight}")
    for pattern, weight in relevance_cfg.get("negative_patterns", {}).items():
        if re.search(pattern, text, flags=re.I):
            score += int(weight)
            negative.append(f"{pattern}:{weight}")
    return {
        "relevance_score": int(score),
        "positive_matches": "; ".join(positive) or None,
        "negative_matches": "; ".join(negative) or None,
        "score_explanation": f"score={score}; positives={len(positive)}; negatives={len(negative)}",
    }
