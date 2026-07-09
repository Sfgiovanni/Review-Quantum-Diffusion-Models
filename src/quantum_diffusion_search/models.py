"""Shared schema constants and lightweight data containers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_COLUMNS = [
    "record_id",
    "run_id",
    "database_scope",
    "retrieval_source",
    "retrieval_method",
    "query_id",
    "query_text",
    "source_record_id",
    "title",
    "title_normalized",
    "abstract",
    "authors",
    "first_author",
    "publication_date",
    "year",
    "updated_date",
    "doi",
    "doi_normalized",
    "arxiv_id",
    "publisher",
    "container_title",
    "document_type",
    "issn",
    "isbn",
    "volume",
    "issue",
    "pages",
    "subjects",
    "categories",
    "license",
    "is_open_access",
    "landing_page_url",
    "abstract_url",
    "pdf_url",
    "raw_source_file",
    "retrieved_at_utc",
    "relevance_score",
    "positive_matches",
    "negative_matches",
    "score_explanation",
    "topic_class",
    "publisher_validation",
    "publisher_validation_reason",
    "duplicate_group_id",
    "merged_sources",
    "screening_status",
    "exclusion_reason",
    "notes",
]


@dataclass
class SearchLogEntry:
    run_id: str
    database_scope: str
    retrieval_source: str
    query_id: str
    query_text: str
    doi_prefix: str | None
    from_pub_date: str
    until_pub_date: str
    started_at_utc: str
    finished_at_utc: str
    api_total_results: int | None = None
    retrieved_records: int = 0
    unique_records_before_cross_source_deduplication: int = 0
    http_requests: int = 0
    retries: int = 0
    truncated: bool = False
    status: str = "ok"
    error_message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
