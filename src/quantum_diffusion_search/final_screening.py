"""Build final manual-screening tables for the review."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

FINAL_COLUMNS = [
    "record_id", "title", "authors", "year", "publication_date", "updated_date", "doi", "arxiv_id", "publisher", "venue",
    "document_type", "abstract", "url", "pdf_url", "all_sources", "all_query_ids", "legacy_notebook_source",
    "legacy_notebook_relevance_score", "new_relevance_score", "automated_topic_class", "screening_decision", "screening_category",
    "review_scope_group", "count_as_quantum_diffusion_model", "recommended_use_in_manuscript", "inclusion_justification_pt",
    "exclusion_reason_code", "screening_basis", "screening_confidence", "manual_verification_required", "duplicate_group_id",
    "preprint_publication_link", "notes", "abstract_source", "abstract_available", "contains_quantum_term", "contains_diffusion_model_term",
    "contains_generative_term", "contains_quantum_computing_context", "contains_physical_diffusion_only", "contains_schrodinger_only",
    "contains_score_matching_in_unrelated_context", "crossref_query_match_quality",
]


def build_final_screening(unique_records: pd.DataFrame, processed_dir: Path, reports_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    for _, row in unique_records.iterrows():
        record = row.to_dict()
        decision = classify_for_review(record)
        rows.append(_final_row(record, decision))
    final = pd.DataFrame(rows)
    for col in FINAL_COLUMNS:
        if col not in final:
            final[col] = pd.NA
    order = {"CORE": 0, "RELATED": 1, "BACKGROUND": 2, "MANUAL_REVIEW": 3, "EXCLUDE": 4}
    final["_order"] = final["screening_category"].map(order).fillna(9)
    final["_year_sort"] = pd.to_numeric(final["year"], errors="coerce").fillna(0)
    final["_rel_sort"] = pd.to_numeric(final["new_relevance_score"], errors="coerce").fillna(0)
    final = final.sort_values(["_order", "_year_sort", "_rel_sort", "title"], ascending=[True, False, False, True]).drop(columns=["_order", "_year_sort", "_rel_sort"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    csv_path = processed_dir / "quantum_diffusion_final_screening.csv"
    xlsx_path = processed_dir / "quantum_diffusion_final_screening.xlsx"
    final[FINAL_COLUMNS].to_csv(csv_path, index=False, encoding="utf-8")
    final[FINAL_COLUMNS].to_excel(xlsx_path, index=False)
    files.extend([str(csv_path), str(xlsx_path)])
    splits = {
        "papers_core.csv": final[final["screening_category"] == "CORE"],
        "papers_related.csv": final[final["screening_category"] == "RELATED"],
        "papers_background.csv": final[final["screening_category"] == "BACKGROUND"],
        "papers_manual_review.csv": final[final["screening_category"] == "MANUAL_REVIEW"],
        "papers_excluded.csv": final[final["screening_category"] == "EXCLUDE"],
    }
    for name, df in splits.items():
        path = processed_dir / name
        df[FINAL_COLUMNS].to_csv(path, index=False, encoding="utf-8")
        files.append(str(path))
    manuscript = final[final["screening_category"].isin(["CORE", "RELATED", "BACKGROUND"])]
    manuscript_csv = processed_dir / "papers_for_manuscript.csv"
    manuscript_xlsx = processed_dir / "papers_for_manuscript.xlsx"
    manuscript[FINAL_COLUMNS].to_csv(manuscript_csv, index=False, encoding="utf-8")
    manuscript[FINAL_COLUMNS].to_excel(manuscript_xlsx, index=False)
    files.extend([str(manuscript_csv), str(manuscript_xlsx)])
    primary = final[final["count_as_quantum_diffusion_model"] == "YES"]
    primary_path = processed_dir / "quantum_diffusion_models_primary_set.csv"
    primary[FINAL_COLUMNS].to_csv(primary_path, index=False, encoding="utf-8")
    files.append(str(primary_path))
    files.append(write_final_screening_report(final, reports_dir / "final_screening_report.md"))
    return final[FINAL_COLUMNS], files


def classify_for_review(record: dict[str, Any]) -> dict[str, Any]:
    title = str(record.get("title") or "")
    abstract = str(record.get("abstract") or "")
    text = f"{title} {abstract} {record.get('subjects') or ''} {record.get('categories') or ''}".lower()
    has_abstract = bool(abstract and abstract.lower() not in {"nan", "none"})
    quantum = bool(re.search(r"\bquantum|qubit|qnn|variational quantum|quantum circuit|quantum neural|quantum hardware|quantum-classical", text))
    diffusion_model = bool(re.search(r"diffusion model|denoising diffusion|ddpm|diffusion probabilistic|latent diffusion|score[- ]based", text))
    denoiser_quantum = bool(re.search(r"quantum neural|qnn|variational quantum|quantum circuit|quantum layer|quantum bottleneck|quantum-classical|quantum random|quantum hardware", text))
    classical_for_quantum_task = bool(re.search(r"quantum circuit synthesis|trotter|gate set tomography|quantum computing task|quantum error|quantum state", text)) and diffusion_model
    quantum_generative_no_diffusion = bool(re.search(r"quantum generative", text)) and not diffusion_model
    schrodinger_bridge = bool(re.search(r"schr[oö]dinger bridge", text))
    physical_only = bool(record.get("contains_physical_diffusion_only")) or (bool(re.search(r"spin diffusion|charge diffusion|thermal diffusion|neutron diffusion|particle diffusion|diffusion equation|advection|transport", text)) and not diffusion_model)
    score_unrelated = bool(record.get("contains_score_matching_in_unrelated_context")) or bool(re.search(r"propensity score", text))
    if physical_only or score_unrelated or (not quantum and not diffusion_model):
        return _decision("EXCLUDE", "EXCLUDE", "Out of scope", "NO", "not_used", _exclude_reason(physical_only, score_unrelated, quantum, diffusion_model), _basis(has_abstract), 0.82, False, title)
    if quantum and diffusion_model and denoiser_quantum:
        return _decision("INCLUDE", "CORE", "G2 - Quantum-enhanced classical diffusion model", "YES", "Core evidence for quantum-enhanced diffusion models", None, _basis(has_abstract), 0.88, False, title)
    if quantum and diffusion_model and re.search(r"state|density matrix|pure-state|quantum state|open quantum", text):
        return _decision("INCLUDE", "CORE", "G1 - Quantum-native diffusion model", "YES", "Core evidence for quantum-native diffusion processes", None, _basis(has_abstract), 0.84, False, title)
    if classical_for_quantum_task:
        return _decision("INCLUDE", "RELATED", "G3 - Classical diffusion model for a quantum-computing task", "NO", "Related method for quantum-computing tasks", None, _basis(has_abstract), 0.78, False, title)
    if quantum_generative_no_diffusion:
        return _decision("INCLUDE", "BACKGROUND", "G5 - Alternative quantum generative model", "NO", "Background comparison for quantum generative modeling", None, _basis(has_abstract), 0.7, False, title)
    if schrodinger_bridge and (quantum or diffusion_model):
        return _decision("INCLUDE", "BACKGROUND", "G6 - Theoretical quantum-diffusion connection", "NO", "Background for mathematical links between diffusion and quantum mechanics", None, _basis(has_abstract), 0.7, False, title)
    if quantum and diffusion_model and not has_abstract:
        return _decision("MANUAL_REVIEW", "MANUAL_REVIEW", "Manual assessment required", "UNCERTAIN", "Manual verification before use", None, _basis(has_abstract), 0.45, True, title)
    if quantum and diffusion_model:
        return _decision("MANUAL_REVIEW", "MANUAL_REVIEW", "Manual assessment required", "UNCERTAIN", "Potentially relevant but requires verification", None, _basis(has_abstract), 0.55, True, title)
    return _decision("EXCLUDE", "EXCLUDE", "Out of scope", "NO", "not_used", "false_positive_terminology", _basis(has_abstract), 0.72, False, title)


def _decision(decision: str, category: str, group: str, count: str, use: str, exclusion: str | None, basis: str, confidence: float, manual: bool, title: str) -> dict[str, Any]:
    if decision == "EXCLUDE":
        justification = f"O registro '{title}' foi recuperado por sobreposição terminológica, mas os metadados indicam que não apresenta um modelo de difusão quântico dentro do escopo do review."
    elif category == "CORE":
        justification = f"O trabalho '{title}' combina terminologia de modelos de difusão com componente quântico metodologicamente relevante, sendo candidato central para a revisão."
    elif category == "RELATED":
        justification = f"O trabalho '{title}' usa modelos de difusão em uma tarefa ligada à computação quântica, mas não deve ser contado como modelo de difusão quântico primário."
    elif category == "BACKGROUND":
        justification = f"O trabalho '{title}' oferece contexto metodológico ou teórico útil para comparar modelos generativos quânticos e difusão."
    else:
        justification = f"Os metadados disponíveis para '{title}' são insuficientes para confirmar se o método satisfaz os critérios de modelo de difusão quântico."
    return {
        "screening_decision": decision,
        "screening_category": category,
        "review_scope_group": group,
        "count_as_quantum_diffusion_model": count,
        "recommended_use_in_manuscript": use,
        "inclusion_justification_pt": justification,
        "exclusion_reason_code": exclusion,
        "screening_basis": basis,
        "screening_confidence": confidence,
        "manual_verification_required": manual,
    }


def _exclude_reason(physical_only: bool, score_unrelated: bool, quantum: bool, diffusion_model: bool) -> str:
    if physical_only:
        return "physical_diffusion_only"
    if score_unrelated:
        return "propensity_or_unrelated_score_matching"
    if not quantum:
        return "not_quantum_related"
    if not diffusion_model:
        return "no_diffusion_model"
    return "false_positive_terminology"


def _basis(has_abstract: bool) -> str:
    return "title+abstract+metadata" if has_abstract else "title+metadata_only"


def _final_row(record: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    abstract = record.get("abstract")
    abstract_available = bool(abstract and str(abstract).lower() not in {"nan", "none"})
    source = "not_available"
    if abstract_available:
        if bool(record.get("arxiv_source")) or record.get("retrieval_source") == "arXiv API":
            source = "arXiv"
        elif "Crossref" in str(record.get("retrieval_source") or record.get("all_sources") or ""):
            source = "Crossref"
        else:
            source = "publisher_metadata"
    return {
        "record_id": record.get("record_id"),
        "title": record.get("title"),
        "authors": record.get("authors"),
        "year": record.get("year"),
        "publication_date": record.get("publication_date"),
        "updated_date": record.get("updated_date"),
        "doi": record.get("doi_normalized") or record.get("doi"),
        "arxiv_id": record.get("arxiv_id"),
        "publisher": record.get("publisher"),
        "venue": record.get("container_title"),
        "document_type": record.get("document_type"),
        "abstract": abstract,
        "url": record.get("landing_page_url") or record.get("abstract_url"),
        "pdf_url": record.get("pdf_url"),
        "all_sources": record.get("all_sources") or record.get("merged_sources") or record.get("database_scope"),
        "all_query_ids": record.get("all_query_ids") or record.get("query_id"),
        "legacy_notebook_source": record.get("legacy_notebook_source"),
        "legacy_notebook_relevance_score": record.get("legacy_notebook_relevance_score"),
        "new_relevance_score": record.get("relevance_score"),
        "automated_topic_class": record.get("topic_class"),
        "duplicate_group_id": record.get("duplicate_group_id"),
        "preprint_publication_link": record.get("preprint_publication_link"),
        "notes": record.get("notes"),
        "abstract_source": source,
        "abstract_available": abstract_available,
        **{k: record.get(k) for k in ["contains_quantum_term", "contains_diffusion_model_term", "contains_generative_term", "contains_quantum_computing_context", "contains_physical_diffusion_only", "contains_schrodinger_only", "contains_score_matching_in_unrelated_context", "crossref_query_match_quality"]},
        **decision,
    }


def write_final_screening_report(final: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final screening report", "",
        "## Criteria", "CORE records directly present quantum-native or quantum-enhanced diffusion methodology. RELATED records use diffusion models for quantum-computing tasks or adjacent denoising. BACKGROUND records support the introduction or theoretical context. EXCLUDE records are false positives or out of scope. MANUAL_REVIEW records require human verification.", "",
        "## Taxonomy", "G1 quantum-native diffusion; G2 quantum-enhanced classical diffusion; G3 classical diffusion for quantum-computing tasks; G4 quantum denoising without diffusion; G5 alternative quantum generative models; G6 theoretical quantum-diffusion connection; G7 classical diffusion background; Out of scope; Manual assessment required.", "",
        "## Counts by category", final["screening_category"].value_counts().to_markdown(), "",
        "## Counts by source", final["all_sources"].fillna("missing").value_counts().to_markdown(), "",
        "## Counts by year", final["year"].fillna("missing").astype(str).value_counts().sort_index().to_markdown(), "",
        "## Main false positives", final.loc[final["screening_category"] == "EXCLUDE", ["title", "exclusion_reason_code"]].head(30).to_markdown(index=False), "",
        "## Records without abstracts", str(int((~final["abstract_available"].astype(bool)).sum())), "",
        "## Manual review required", final.loc[final["screening_category"] == "MANUAL_REVIEW", ["title", "screening_basis", "inclusion_justification_pt"]].to_markdown(index=False), "",
        "## Limitations", "Automated decisions are conservative and based on public metadata. Records without abstracts require human verification. IEEE and Springer scopes are Crossref DOI-prefix searches, not direct proprietary API searches.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
