"""Method-library input gates for capability A (schema match before Host).

Deterministic checks only. No Longevity-LLM. Used by Host tooling docs and
future callers that want to refuse a formula when units / features mismatch.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence


# Clinical age / mortality prompts often mix SI and conventional units.
CLINICAL_UNIT_ALIASES = {
    "creatinine": {"mg/dl": 1.0, "mg/dL": 1.0, "umol/l": 1 / 88.4, "µmol/l": 1 / 88.4},
    "glucose": {"mg/dl": 1.0, "mg/dL": 1.0, "mmol/l": 1 / 18.0},
}

# Fixed-site clocks that must not claim applicability on rotating-site exam prompts.
FIXED_METHYLATION_CLOCKS = ("epiage", "pyaging", "horvath", "hannum", "dunedinpace")

# PhenoAge / Levine clinical clocks need chronological age; LongevityBench age
# pairwise asks for age, so these member methods must not be called on that schema.
PHENOAGE_METHODS = (
    "accelerated-biological-aging-risk",
    "phenoage",
    "levine",
)

# Name-lookup databases: refuse when the gene is masked (Gene X) or the prompt is an exam.
GENE_DB_METHODS = ("opengenes", "synergy-age", "synergyage")


def normalize_clinical_value(marker: str, value: float, unit: str) -> Dict[str, Any]:
    """Convert a clinical marker to the conventional unit used by formula weights."""
    key = marker.strip().lower()
    table = CLINICAL_UNIT_ALIASES.get(key)
    if not table:
        return {"ok": False, "reason": f"no unit table for {marker!r}", "value": value, "unit": unit}
    u = unit.strip()
    # tolerate µmol spelling
    if u.lower() in ("umol/l", "µmol/l", "umol/L"):
        factor = table.get("umol/l") or table.get("µmol/l")
    else:
        factor = None
        for k, f in table.items():
            if k.lower() == u.lower():
                factor = f
                break
    if factor is None:
        return {"ok": False, "reason": f"unknown unit {unit!r} for {marker}", "value": value, "unit": unit}
    return {
        "ok": True,
        "marker": key,
        "value_conventional": float(value) * float(factor),
        "from_unit": unit,
        "to_unit": "mg/dl",
    }


def features_present(required: Sequence[str], available: Iterable[str]) -> Dict[str, Any]:
    have = {a.strip().lower() for a in available}
    missing = [r for r in required if r.strip().lower() not in have]
    return {
        "ok": not missing,
        "missing": missing,
        "n_required": len(required),
        "n_present": len(required) - len(missing),
    }


def refuse_fixed_clock_on_rotating_sites(
    method_id: str,
    site_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Gate: fixed CpG clocks are uncovered on LongevityBench-style rotating sites."""
    mid = (method_id or "").strip().lower()
    blocked = any(tok in mid for tok in FIXED_METHYLATION_CLOCKS)
    return {
        "ok": not blocked,
        "method_id": method_id,
        "refuse": blocked,
        "reason": (
            "fixed-site clock not applicable to rotating-site / exam methylation prompts; use Host+tools"
            if blocked
            else "ok"
        ),
        "n_sites_shown": len(site_ids or []),
    }


def refuse_phenoage_without_chrono_age(
    method_id: str,
    chronological_age_present: bool = False,
) -> Dict[str, Any]:
    """Gate: PhenoAge-family methods need chronological age; exam age tasks do not provide it."""
    mid = (method_id or "").strip().lower()
    is_pheno = any(tok in mid for tok in PHENOAGE_METHODS)
    blocked = bool(is_pheno and not chronological_age_present)
    if not is_pheno:
        reason = "ok"
    elif chronological_age_present:
        reason = "ok"
    else:
        reason = (
            "PhenoAge / accelerated-biological-aging-risk requires chronological age; "
            "not applicable when age is the unknown (exam pairwise / member age-blind compare); "
            "use clinical comparator formula or Host+tools"
        )
    return {
        "ok": not blocked,
        "method_id": method_id,
        "refuse": blocked,
        "chronological_age_present": bool(chronological_age_present),
        "reason": reason,
    }


def refuse_gene_db_on_masked_exam(
    method_id: str,
    gene_name_masked: bool = True,
) -> Dict[str, Any]:
    """Gate: OpenGenes / SynergyAge must not be queried when the gene is masked or on exam prompts."""
    mid = (method_id or "").strip().lower().replace("_", "-")
    is_db = any(tok in mid for tok in GENE_DB_METHODS)
    blocked = bool(is_db and gene_name_masked)
    if not is_db:
        reason = "ok"
    elif not gene_name_masked:
        reason = "ok"
    else:
        reason = (
            "gene name is masked or this is an exam prompt; do not query OpenGenes / SynergyAge "
            "(lookup would be N/A or leak the answer); use Host+tools"
        )
    return {
        "ok": not blocked,
        "method_id": method_id,
        "refuse": blocked,
        "gene_name_masked": bool(gene_name_masked),
        "reason": reason,
    }


def safety_gate_intervention(
    flags: Dict[str, bool],
) -> Dict[str, Any]:
    """Capability B helper: if any contraindication flag is set, longevity Rx is not first-line."""
    active = [k for k, v in (flags or {}).items() if v]
    return {
        "ok": True,
        "longevity_first_line": len(active) == 0,
        "active_flags": active,
        "recommendation_bias": "no" if active else "case_by_case",
        "note": "Feeds Host structured advice; does not replace clinical care.",
    }
