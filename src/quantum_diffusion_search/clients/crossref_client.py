"""Crossref REST API client and parser."""

from __future__ import annotations

import gzip
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from ..normalization import clean_text, crossref_list, extract_year, normalize_doi, normalize_title, parse_crossref_date


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def parse_crossref_item(
    item: dict[str, Any],
    *,
    query_id: str,
    query_text: str,
    run_id: str,
    database_scope: str,
    retrieval_method: str,
    doi_prefix: str,
    raw_source_file: str,
) -> dict[str, Any]:
    doi_norm = normalize_doi(item.get("DOI"))
    authors = []
    for author in item.get("author") or []:
        name = clean_text(" ".join(x for x in [author.get("given"), author.get("family")] if x))
        if name:
            authors.append(name)
    title = clean_text(_first(item.get("title")))
    pub_date = (
        parse_crossref_date(item.get("published-print"))
        or parse_crossref_date(item.get("published-online"))
        or parse_crossref_date(item.get("issued"))
    )
    publisher = clean_text(item.get("publisher"))
    container_title = clean_text(_first(item.get("container-title")))
    valid_prefix = bool(doi_norm and doi_norm.startswith(doi_prefix.lower() + "/"))
    publisher_hint = "valid" if valid_prefix else "invalid"
    reason = f"DOI prefix {'matches' if valid_prefix else 'does not match'} {doi_prefix}; publisher={publisher}"
    license_entries = item.get("license") or []
    return {
        "run_id": run_id,
        "database_scope": database_scope,
        "retrieval_source": "Crossref",
        "retrieval_method": retrieval_method,
        "query_id": query_id,
        "query_text": query_text,
        "source_record_id": doi_norm,
        "title": title,
        "title_normalized": normalize_title(title),
        "abstract": clean_text(item.get("abstract")),
        "authors": "; ".join(authors) or None,
        "first_author": authors[0] if authors else None,
        "publication_date": pub_date,
        "year": extract_year(pub_date),
        "updated_date": parse_crossref_date(item.get("deposited")),
        "doi": item.get("DOI"),
        "doi_normalized": doi_norm,
        "arxiv_id": None,
        "publisher": publisher,
        "container_title": container_title,
        "document_type": clean_text(item.get("type")),
        "issn": crossref_list(item.get("ISSN")),
        "isbn": crossref_list(item.get("ISBN")),
        "volume": clean_text(item.get("volume")),
        "issue": clean_text(item.get("issue")),
        "pages": clean_text(item.get("page")),
        "subjects": crossref_list(item.get("subject")),
        "categories": None,
        "license": crossref_list([lic.get("URL") for lic in license_entries if isinstance(lic, dict)]),
        "is_open_access": bool(license_entries) if license_entries else None,
        "landing_page_url": item.get("URL") or (f"https://doi.org/{doi_norm}" if doi_norm else None),
        "abstract_url": None,
        "pdf_url": None,
        "raw_source_file": raw_source_file,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "publisher_validation": publisher_hint,
        "publisher_validation_reason": reason,
        "screening_status": "not_screened",
    }


class CrossrefClient:
    endpoint = "https://api.crossref.org/prefixes/{prefix}/works"

    def __init__(self, cfg: dict[str, Any], raw_dir: Path):
        self.cfg = cfg
        self.raw_dir = raw_dir
        self.session = requests.Session()
        mailto = os.environ.get("CROSSREF_MAILTO")
        ua = cfg["api"].get("user_agent", "quantum-diffusion-literature-search/1.0")
        if mailto:
            ua = f"{ua} (mailto:{mailto})"
        self.session.headers.update({"User-Agent": ua})
        self.http_requests = 0
        self.retries = 0

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        api_cfg = self.cfg["api"]
        for attempt in range(int(api_cfg["max_attempts"])):
            self.http_requests += 1
            response = self.session.get(url, params=params, timeout=float(api_cfg["timeout_seconds"]))
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == int(api_cfg["max_attempts"]) - 1:
                    response.raise_for_status()
                self.retries += 1
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(
                    float(api_cfg["backoff"]["max_seconds"]),
                    float(api_cfg["backoff"]["initial_seconds"]) * (float(api_cfg["backoff"]["multiplier"]) ** attempt),
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                raise ValueError(f"Crossref returned invalid JSON for params={params}") from exc
            if data.get("status") != "ok" or "message" not in data:
                raise ValueError(f"Unexpected Crossref response shape for params={params}")
            return data
        raise RuntimeError("Crossref retry loop exited unexpectedly")

    def fetch_query(
        self,
        query: dict[str, Any],
        run_id: str,
        database_scope: str,
        retrieval_method: str,
        doi_prefix: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        api_cfg = self.cfg["api"]
        date_range = self.cfg["date_range"]
        rows = int(api_cfg["batch_size"])
        max_results = int(api_cfg["max_results_per_query"])
        cursor = "*"
        retrieved = 0
        page = 0
        all_rows: list[dict[str, Any]] = []
        total_results = None
        truncated = False
        while retrieved < max_results:
            params = {
                "query.bibliographic": query["crossref_query"],
                "filter": f"from-pub-date:{date_range['from_pub_date']},until-pub-date:{date_range['until_pub_date']}",
                "rows": min(rows, max_results - retrieved),
                "cursor": cursor,
                "select": "DOI,title,author,publisher,container-title,type,issued,published-print,published-online,deposited,ISSN,ISBN,volume,issue,page,subject,license,URL,abstract",
            }
            raw_file = self.raw_dir / f"{query['query_id']}_{doi_prefix.replace('.', '_')}_page{page}.json.gz"
            params_file = self.raw_dir / f"{query['query_id']}_{doi_prefix.replace('.', '_')}_page{page}_params.json"
            if raw_file.exists():
                with gzip.open(raw_file, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = self._get_json(self.endpoint.format(prefix=doi_prefix), params)
                with gzip.open(raw_file, "wt", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                params_file.write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
                time.sleep(float(api_cfg["sleep_seconds"]))
            message = data["message"]
            total_results = int(message.get("total-results", 0))
            items = message.get("items") or []
            if not isinstance(items, list):
                raise ValueError("Crossref response message.items is not a list.")
            parsed = [
                parse_crossref_item(
                    item,
                    query_id=query["query_id"],
                    query_text=query["crossref_query"],
                    run_id=run_id,
                    database_scope=database_scope,
                    retrieval_method=retrieval_method,
                    doi_prefix=doi_prefix,
                    raw_source_file=str(raw_file),
                )
                for item in items
            ]
            all_rows.extend([r for r in parsed if r.get("doi_normalized", "").startswith(doi_prefix.lower() + "/")])
            retrieved += len(items)
            next_cursor = message.get("next-cursor")
            if not items or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
            page += 1
        # Flag truncation whenever the API reports more results than we retrieved,
        # not only when the max-results cap was hit.
        if total_results is not None and total_results > retrieved:
            truncated = True
        return all_rows, {"api_total_results": total_results, "retrieved_records": len(all_rows), "truncated": truncated}
