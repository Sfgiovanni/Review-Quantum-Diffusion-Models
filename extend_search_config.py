#!/usr/bin/env python3
"""Extend the search configuration to retrieve diffusion-based quantum
circuit-synthesis papers (e.g. Q-Fusion arXiv:2504.20794 and Barta et al.
arXiv:2505.20863), which the original 18 queries did not surface.

Idempotent and anchor-checked. Run from the repository root:

    python extend_search_config.py            # patches both search configs
    python extend_search_config.py configs/search_config.yaml  # a specific file
"""

from __future__ import annotations

import sys
from pathlib import Path

NEW_QUERIES = """- query_id: Q19
  concept: diffusing quantum circuits
  arxiv_query: all:"diffusing quantum circuits"
  crossref_query: '"diffusing quantum circuits"'
  rationale: Diffusion-based generation of quantum circuits (e.g. Q-Fusion, arXiv:2504.20794).
  strategy: high_precision
- query_id: Q20
  concept: diffusion parameterized quantum circuit
  arxiv_query: all:"diffusion" AND all:"parameterized quantum circuit"
  crossref_query: diffusion "parameterized quantum circuit"
  rationale: Diffusion synthesis of parameterized quantum circuits (e.g. Barta et al., arXiv:2505.20863).
  strategy: high_recall
- query_id: Q21
  concept: quantum circuit synthesis diffusion
  arxiv_query: all:"quantum circuit synthesis" AND all:"diffusion"
  crossref_query: '"quantum circuit synthesis" diffusion'
  rationale: Diffusion models for quantum circuit synthesis (e.g. genQC, arXiv:2311.02041).
  strategy: high_recall
- query_id: Q22
  concept: quantum architecture search diffusion
  arxiv_query: all:"quantum architecture search" AND all:"diffusion"
  crossref_query: '"quantum architecture search" diffusion'
  rationale: Diffusion-based quantum architecture search.
  strategy: high_recall
- query_id: Q23
  concept: diffusion quantum circuit generation
  arxiv_query: all:"diffusion" AND all:"quantum circuit generation"
  crossref_query: diffusion "quantum circuit generation"
  rationale: Broad recall for diffusion-driven quantum circuit generation.
  strategy: high_recall
"""

NEW_RELEVANCE = (
    "    \\bquantum circuit synthesis\\b: 5\n"
    "    \\bquantum circuit generation\\b: 4\n"
    "    \\bquantum architecture search\\b: 4\n"
    "    \\bparameterized quantum circuit(s)?\\b: 3\n"
    "    \\bdiffusing quantum circuits\\b: 7\n"
)

NEW_TOPIC = (
    "  diffusion-based quantum circuit synthesis:\n"
    "  - quantum circuit generation\n"
    "  - quantum architecture search\n"
    "  - diffusing quantum circuits\n"
    "  - quantum circuit synthesis\n"
)

# (sentinel to detect prior application, anchor, mode) ; mode: "before" or "after"
INSERTIONS = [
    ("query_id: Q19", "run_mode: full", NEW_QUERIES, "before"),
    ("diffusing quantum circuits\\b: 7", "    \\bquantum circuit(s)?\\b: 3\n", NEW_RELEVANCE, "after"),
    ("diffusion-based quantum circuit synthesis:", "  quantum circuit diffusion:\n  - quantum circuit\n", NEW_TOPIC, "after"),
    # Pin the upper cutoff so "up to mid-2026" is frozen and reproducible (all-years scope).
    ("until_pub_date: '2026-07-09'", "until_pub_date: null", "until_pub_date: '2026-07-09'", "replace"),
]


def patch_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for sentinel, anchor, addition, mode in INSERTIONS:
        if sentinel in text:
            continue
        if text.count(anchor) != 1:
            return f"[FAIL] {path}: anchor found {text.count(anchor)} times (expected 1): {anchor[:40]!r}"
        if mode == "before":
            text = text.replace(anchor, addition + anchor)
        elif mode == "after":
            text = text.replace(anchor, anchor + addition)
        else:  # replace
            text = text.replace(anchor, addition)
    path.write_text(text, encoding="utf-8")
    return f"[ok] extended {path}"


def main() -> int:
    if len(sys.argv) > 1:
        targets = [Path(a) for a in sys.argv[1:]]
    else:
        targets = [Path("configs/search_config.yaml"), Path("configs/search_config_full.yaml")]
    rc = 0
    for path in targets:
        if not path.exists():
            print(f"[skip] {path} not found")
            continue
        msg = patch_file(path)
        print(msg)
        if msg.startswith("[FAIL]"):
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
