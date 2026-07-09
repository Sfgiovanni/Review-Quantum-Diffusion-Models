"""Crossref/local query quality indicators."""

from __future__ import annotations

import re
from typing import Any


def _text(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(k) or "") for k in ["title", "abstract", "subjects", "categories", "container_title"]).lower()


def query_quality_indicators(record: dict[str, Any]) -> dict[str, Any]:
    text = _text(record)
    contains_quantum_term = bool(re.search(r"\bquantum|qubit|qnn|variational quantum|quantum circuit|quantum neural", text))
    contains_diffusion_model_term = bool(re.search(r"diffusion model|denoising diffusion|ddpm|score[- ]based|score matching|latent diffusion", text))
    contains_generative_term = bool(re.search(r"generative|generation|denois|sample|sampling|score[- ]based|ddpm|diffusion probabilistic", text))
    contains_quantum_computing_context = bool(re.search(r"quantum circuit|qubit|quantum neural|variational quantum|qnn|quantum machine learning|quantum computing|quantum hardware", text))
    contains_physical_diffusion_only = bool(re.search(r"spin diffusion|charge diffusion|thermal diffusion|neutron diffusion|particle diffusion|mass diffusion|advection|transport equation|diffusion equation", text)) and not contains_diffusion_model_term
    contains_schrodinger_only = bool(re.search(r"schr[oö]dinger", text)) and not bool(re.search(r"bridge|generative|denois|diffusion model|score[- ]based", text))
    contains_score_matching_in_unrelated_context = bool(re.search(r"propensity score|matching score|score matching", text)) and not contains_diffusion_model_term and not contains_quantum_computing_context
    if contains_quantum_term and contains_diffusion_model_term and (contains_generative_term or contains_quantum_computing_context):
        quality = "high"
    elif contains_quantum_term and (contains_diffusion_model_term or contains_generative_term):
        quality = "medium"
    elif contains_physical_diffusion_only or contains_score_matching_in_unrelated_context:
        quality = "false_positive_likely"
    else:
        quality = "low"
    return {
        "contains_quantum_term": contains_quantum_term,
        "contains_diffusion_model_term": contains_diffusion_model_term,
        "contains_generative_term": contains_generative_term,
        "contains_quantum_computing_context": contains_quantum_computing_context,
        "contains_physical_diffusion_only": contains_physical_diffusion_only,
        "contains_schrodinger_only": contains_schrodinger_only,
        "contains_score_matching_in_unrelated_context": contains_score_matching_in_unrelated_context,
        "crossref_query_match_quality": quality,
    }
