"""arXiv API client and parser."""

from __future__ import annotations

import json
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import feedparser
import requests

from ..normalization import clean_text, doi_from_text, extract_year, normalize_doi, normalize_title, strip_arxiv_version


def parse_arxiv_entry(entry: Any, *, query_id: str, query_text: str, run_id: str, raw_source_file: str) -> dict[str, Any]:
    arxiv_id = str(getattr(entry, "id", "")).split("/abs/")[-1]
    arxiv_base = strip_arxiv_version(arxiv_id)
    categories = [tag.get("term", "") for tag in getattr(entry, "tags", []) if tag.get("term")]
    pdf_url = None
    for link in getattr(entry, "links", []):
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href")
            break
    authors = [getattr(author, "name", "") for author in getattr(entry, "authors", []) if getattr(author, "name", "")]
    title = clean_text(getattr(entry, "title", None))
    abstract = clean_text(getattr(entry, "summary", None))
    doi = normalize_doi(getattr(entry, "arxiv_doi", None)) or doi_from_text(getattr(entry, "arxiv_journal_ref", None))
    return {
        "run_id": run_id,
        "database_scope": "arXiv",
        "retrieval_source": "arXiv API",
        "retrieval_method": "arXiv API search",
        "query_id": query_id,
        "query_text": query_text,
        "source_record_id": arxiv_base,
        "title": title,
        "title_normalized": normalize_title(title),
        "abstract": abstract,
        "authors": "; ".join(authors) or None,
        "first_author": authors[0] if authors else None,
        "publication_date": getattr(entry, "published", None),
        "year": extract_year(getattr(entry, "published", None)),
        "updated_date": getattr(entry, "updated", None),
        "doi": clean_text(getattr(entry, "arxiv_doi", None)),
        "doi_normalized": doi,
        "arxiv_id": arxiv_base,
        "publisher": "arXiv",
        "container_title": clean_text(getattr(entry, "arxiv_journal_ref", None)),
        "document_type": "preprint",
        "categories": "; ".join(categories) or None,
        "abstract_url": getattr(entry, "link", None),
        "pdf_url": pdf_url or (f"https://arxiv.org/pdf/{arxiv_base}" if arxiv_base else None),
        "landing_page_url": getattr(entry, "link", None),
        "raw_source_file": raw_source_file,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "publisher_validation": "valid",
        "publisher_validation_reason": "Retrieved from arXiv public API.",
        "screening_status": "not_screened",
    }


class ArxivClient:
    def __init__(self, cfg: dict[str, Any], raw_dir: Path):
        self.cfg = cfg
        self.raw_dir = raw_dir
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": cfg["api"].get("user_agent", "quantum-diffusion-search")})
        self.http_requests = 0
        self.retries = 0

    def fetch_query(self, query: dict[str, Any], run_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        api_cfg = self.cfg["api"]
        batch = int(api_cfg["batch_size"])
        max_results = int(api_cfg["max_results_per_query"])
        sleep_seconds = float(api_cfg["sleep_seconds"])
        timeout = float(api_cfg["timeout_seconds"])
        max_attempts = int(api_cfg["max_attempts"])
        rows: list[dict[str, Any]] = []
        start = 0
        total_results = None
        truncated = False
        query_text = query["arxiv_query"]
        while start < max_results:
            current_batch = min(batch, max_results - start)
            params = {
                "search_query": query_text,
                "start": start,
                "max_results": current_batch,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
            raw_file = self.raw_dir / f"{query['query_id']}_start{start}.xml"
            if raw_file.exists():
                content = raw_file.read_bytes()
            else:
                for attempt in range(max_attempts):
                    try:
                        self.http_requests += 1
                        response = self.session.get(url, timeout=timeout)
                        response.raise_for_status()
                        content = response.content
                        raw_file.write_bytes(content)
                        break
                    except requests.RequestException:
                        if attempt == max_attempts - 1:
                            raise
                        self.retries += 1
                        time.sleep(min(api_cfg["backoff"]["max_seconds"], api_cfg["backoff"]["initial_seconds"] * (2**attempt)))
                else:
                    content = b""
            feed = feedparser.parse(content)
            if getattr(feed, "bozo", False):
                raise ValueError(f"Invalid arXiv feed for {query['query_id']}: {getattr(feed, 'bozo_exception', '')}")
            if total_results is None:
                total_results = int(getattr(feed.feed, "opensearch_totalresults", 0) or 0)
            entries = getattr(feed, "entries", [])
            if not entries:
                break
            rows.extend(
                parse_arxiv_entry(e, query_id=query["query_id"], query_text=query_text, run_id=run_id, raw_source_file=str(raw_file))
                for e in entries
            )
            start += len(entries)
            if len(entries) < current_batch:
                break
            if start < max_results:
                time.sleep(sleep_seconds)
        if total_results is not None and total_results > len(rows) and len(rows) >= max_results:
            truncated = True
        meta = {"api_total_results": total_results, "retrieved_records": len(rows), "truncated": truncated}
        (self.raw_dir / f"{query['query_id']}_params.json").write_text(json.dumps({"query": query, "meta": meta}, indent=2), encoding="utf-8")
        return rows, meta
