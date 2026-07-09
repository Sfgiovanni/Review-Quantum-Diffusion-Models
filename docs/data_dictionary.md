# Data Dictionary

The unified schema is defined in `src/quantum_diffusion_search/models.py`.

Key fields include source provenance (`run_id`, `database_scope`, `retrieval_source`, `retrieval_method`, `query_id`, `raw_source_file`), bibliographic metadata (`title`, `authors`, `publication_date`, `doi_normalized`, `container_title`, `document_type`), processing fields (`relevance_score`, `topic_class`, `publisher_validation`, `duplicate_group_id`, `merged_sources`), and manual screening fields (`screening_status`, `exclusion_reason`, `notes`).

Missing values are stored as nulls where supported by the output format.
