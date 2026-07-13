#!/usr/bin/env python3
"""Apply the in-place source edits for the reproducibility hardening.

Run once from the repository root:

    python apply_patches.py

It patches three existing files (idempotently):
  * src/quantum_diffusion_search/cli.py            - wires `reproduce` (real) and `apply-screening`, fixes PRISMA labels
  * src/quantum_diffusion_search/clients/arxiv_client.py     - truncation detection
  * src/quantum_diffusion_search/clients/crossref_client.py  - truncation detection

New files (reproduce.py, apply_screening.py, tests, data/screening/*, lock files)
are shipped alongside and do not need patching.
"""

from __future__ import annotations

import sys
from pathlib import Path

EDITS: dict[str, list[tuple[str, str]]] = {
    "src/quantum_diffusion_search/cli.py": [
        # 1. Register the apply-screening subcommand.
        (
            '    p = sub.add_parser("reproduce")\n'
            '    p.add_argument("--raw-run", required=True)\n'
            "    args = parser.parse_args(argv)",
            '    p = sub.add_parser("reproduce")\n'
            '    p.add_argument("--raw-run", required=True)\n'
            '    p = sub.add_parser("apply-screening")\n'
            '    p.add_argument("--screening", default="data/screening/manual_screening.csv")\n'
            '    p.add_argument("--processed", default="data/processed")\n'
            '    p.add_argument("--reports", default="reports")\n'
            '    p.add_argument("--corpus-from", type=int, default=2025)\n'
            '    p.add_argument("--corpus-to", type=int, default=2026)\n'
            "    args = parser.parse_args(argv)",
        ),
        # 2. Dispatch apply-screening.
        (
            '    if args.command == "reproduce":\n'
            "        return run_reproduce(Path(args.raw_run))\n"
            "    return 2",
            '    if args.command == "reproduce":\n'
            "        return run_reproduce(Path(args.raw_run))\n"
            '    if args.command == "apply-screening":\n'
            "        from .apply_screening import apply_screening\n"
            "        summary = apply_screening(Path(args.screening), Path(args.processed), Path(args.reports), corpus_from=args.corpus_from, corpus_to=args.corpus_to)\n"
            "        for key, value in summary.items():\n"
            '            print(f"{key}: {value}")\n'
            "        return 0\n"
            "    return 2",
        ),
        # 3. Replace the stub reproduce with the real reconstruction.
        (
            "def run_reproduce(raw_run: Path) -> int:\n"
            "    cfg_path = raw_run / \"resolved_search_config.yaml\"\n"
            "    if not cfg_path.exists():\n"
            "        raise FileNotFoundError(cfg_path)\n"
            "    records: list[dict[str, Any]] = []\n"
            '    for raw_file in raw_run.rglob("*.json.gz"):\n'
            '        if "_params" in raw_file.name:\n'
            "            continue\n"
            "        # Reproduction from raw Crossref files is intentionally conservative here.\n"
            "        # The original manifest and raw payloads remain the authoritative acquisition record.\n"
            "        pass\n"
            '    if not records and Path("data/processed/all_source_records.csv").exists():\n'
            '        shutil.copy("data/processed/all_source_records.csv", "data/processed/all_source_records_reproduced.csv")\n'
            "    return 0",
            "def run_reproduce(raw_run: Path) -> int:\n"
            "    from .reproduce import reproduce_run\n"
            "\n"
            "    return reproduce_run(raw_run)",
        ),
        # 4a. Clarify the automated labels in search_report.md.
        (
            '    lines.extend([f"- {k}: {v}" for k, v in counts.items()])',
            '    lines.extend([f"- {k}: {v}" for k, v in counts.items()])\n'
            "    lines.extend([\n"
            '        "",\n'
            '        "> Note: CORE/RELATED/BACKGROUND and \'primary quantum-diffusion models\' are automated",\n'
            '        "> labels applied to cross-source records before deduplication; they are screening aids,",\n'
            '        "> not the final included set. Unique-candidate, included, excluded and pending counts are",\n'
            '        "> produced by `apply-screening` (see reports/selection_flow.md).",\n'
            "    ])",
        ),
        # 4b. Relabel the misleading PRISMA rows.
        (
            '        ("records included as CORE", counts["CORE"], "automated metadata screening"),',
            '        ("automated CORE labels (cross-source records, pre-deduplication)", counts["CORE"], "automated metadata screening"),',
        ),
        (
            '        ("primary quantum-diffusion studies", counts["Primary quantum-diffusion models"], "computed"),',
            '        ("automated CORE candidates for manual screening (cross-source)", counts["Primary quantum-diffusion models"], "screening aid, not final inclusion"),',
        ),
    ],
    "src/quantum_diffusion_search/clients/arxiv_client.py": [
        (
            "        if total_results is not None and total_results > len(rows) and len(rows) >= max_results:\n"
            "            truncated = True",
            "        # Flag truncation whenever the API reports more results than we retrieved,\n"
            "        # not only when the max-results cap was hit (an early stop is also a partial query).\n"
            "        if total_results is not None and total_results > len(rows):\n"
            "            truncated = True",
        ),
    ],
    "src/quantum_diffusion_search/clients/crossref_client.py": [
        (
            "        if total_results is not None and total_results > retrieved and retrieved >= max_results:\n"
            "            truncated = True",
            "        # Flag truncation whenever the API reports more results than we retrieved,\n"
            "        # not only when the max-results cap was hit.\n"
            "        if total_results is not None and total_results > retrieved:\n"
            "            truncated = True",
        ),
    ],
}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    problems: list[str] = []
    for rel, edits in EDITS.items():
        path = root / rel
        if not path.exists():
            problems.append(f"missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            if new in text and old not in text:
                print(f"[skip] already applied: {rel}")
                continue
            count = text.count(old)
            if count != 1:
                problems.append(f"{rel}: anchor found {count} times (expected 1): {old[:60]!r}")
                continue
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"[ok] patched {rel}")
    if problems:
        print("\nPROBLEMS (no partial writes for these):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nAll patches applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
