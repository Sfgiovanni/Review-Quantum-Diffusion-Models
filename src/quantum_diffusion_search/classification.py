"""Rule-based multi-label topic classification."""

from __future__ import annotations

import re
from typing import Any


def classify_record(record: dict[str, Any], topic_patterns: dict[str, list[str]]) -> str:
    text = " ".join(str(record.get(k) or "") for k in ["title", "abstract", "subjects", "categories"]).lower()
    labels = []
    for label, patterns in topic_patterns.items():
        if any(re.search(pattern, text, flags=re.I) for pattern in patterns):
            labels.append(label)
    return "; ".join(labels) if labels else "other / manual assessment required"
