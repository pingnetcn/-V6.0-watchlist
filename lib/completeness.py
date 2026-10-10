"""
Quality + credibility scoring wrapper (no LLM calls).

How to extend:
    Add new scoring dimension by composing existing credibility_scorer
    NEVER call LLM here — pure analysis of existing report only

Public API:
    score_one(report_path) -> dict
    score_batch(codes) -> DataFrame
    aggregate_dashboard(codes) -> dict
"""
import sys
from pathlib import Path
import pandas as pd

from lib.paths import MAIN_PROJECT
if str(MAIN_PROJECT) not in sys.path:
    sys.path.insert(0, str(MAIN_PROJECT))

from tradingagents.valuation_synthesizer.credibility_scorer import (
    compute_credibility_score_from_report,
)
from lib.valuation_reader import parse_metadata, latest_version

# Lazy-import valuation_quality_check: main project's tradingagents.agents.__init__
# transitively imports langchain_core, which the watchlist venv deliberately omits.
# We attempt the import lazily; if it fails, fall back to metadata's pre-computed
# quality_grade (written by quality_gate at report time, identical logic).
_VALUATION_QUALITY_CHECK = None
_QUALITY_CHECK_IMPORT_ERROR: Exception | None = None
try:
    from tradingagents.agents.quality_gate import (
        valuation_quality_check as _valuation_quality_check_from_main,
    )
    _VALUATION_QUALITY_CHECK = _valuation_quality_check_from_main
except Exception as _exc:  # ModuleNotFoundError langchain_core, etc.
    _QUALITY_CHECK_IMPORT_ERROR = _exc

SCHEMA_VERSION = 1


def _to_state(meta: dict) -> dict:
    """Adapter: metadata dict -> state dict for valuation_quality_check.

    Key names mirror tradingagents.agents.quality_gate.valuation_quality_check:
      state['valuation_rating'], state['valuation_intrinsic'], etc.
    """
    return {
        "valuation_analysis_report": "",
        "valuation_rating": meta.get("rating", "C"),
        "valuation_intrinsic": meta.get("intrinsic_value", 0),
        "valuation_margin": meta.get("margin", 0),
        "valuation_failure_modes": meta.get("failure_modes", []),
        "valuation_ttm_source": meta.get("ttm_source", "em_db"),
    }


def _quality_check_local(state: dict, meta: dict) -> dict:
    """Local fallback when quality_gate is unimportable.

    Mirrors the 5 simple checks in tradingagents.agents.quality_gate
    (rating format + intrinsic>0 + |margin|<500 + failure_modes count),
    then degrades to metadata['quality_grade'] when checks don't downgrade.
    """
    grade = "A"
    issues = []
    rating = state.get("valuation_rating") or meta.get("rating", "")
    intrinsic = state.get("valuation_intrinsic", 0)
    margin = state.get("valuation_margin", 0)
    fms = state.get("valuation_failure_modes") or []
    ttm = state.get("valuation_ttm_source", "em_db")

    if rating and rating not in {"A+", "A", "B+", "B", "C", "D", "F"}:
        issues.append(f"评级格式异常: {rating}")
        grade = "D"
    elif not rating:
        issues.append("评级缺失")
        grade = "D"
    if intrinsic <= 0:
        issues.append(f"内在价值非正({intrinsic})")
        grade = "D"
    if abs(margin) > 500:
        issues.append(f"margin 异常({margin:.0f}%)")
        grade = max(grade, "C", key=lambda x: "ABCDF".index(x))
    if len(fms) > 5:
        issues.append(f"失败模式触发过多({len(fms)}项)")
        grade = max(grade, "C", key=lambda x: "ABCDF".index(x))
    if isinstance(ttm, str) and ttm.startswith("akshare"):
        issues.append("TTM 数据 AkShare 兜底")
        grade = max(grade, "B", key=lambda x: "ABCDF".index(x))

    # If metadata already carries a canonical quality_grade, prefer it.
    meta_grade = meta.get("quality_grade")
    if meta_grade in {"A+", "A", "B+", "B", "C", "D", "F"} and grade == "A":
        grade = meta_grade

    if not issues:
        issues.append("quality_grade from metadata")

    return {
        "valuation_quality_grade": grade,
        "valuation_hard_fail": grade == "F",
        "valuation_quality_issues": issues,
    }


def score_one(report_path: Path) -> dict:
    meta = parse_metadata(report_path)
    state = _to_state(meta)
    report_text = Path(report_path).read_text(encoding="utf-8", errors="replace")
    methods_used = meta.get("methods_used") or []
    methods_spread = float(meta.get("methods_spread") or 0)

    cred_result = compute_credibility_score_from_report(
        report_text,
        methods_spread=methods_spread,
        fcff_failed=False,
        valid_methods_count=len(methods_used),
        failure_result=None,
        company_type=meta.get("company_type", "稳定价值股"),
        methods_used=methods_used,
        margin=meta.get("margin"),
        fins_5y=[],
        valuation_metrics=None,
        data_as_of_date=meta.get("generated_at"),
        trade_date=None,
    )

    if _VALUATION_QUALITY_CHECK is not None:
        quality = _VALUATION_QUALITY_CHECK(state)
    else:
        quality = _quality_check_local(state, meta)

    return {
        "credibility_score": getattr(cred_result, "total", 0),
        "credibility_tier": meta.get("credibility", "中"),
        "quality_grade": quality.get("valuation_quality_grade", "C"),
        "hard_fail": quality.get("valuation_hard_fail", False),
        "failure_modes": meta.get("failure_modes", []),
        "methods_spread": methods_spread,
    }


def score_batch(codes: list[str]) -> pd.DataFrame:
    rows = []
    for code in codes:
        path = latest_version(code)
        if path is None:
            continue
        score = score_one(path)
        score["code"] = code
        rows.append(score)
    return pd.DataFrame(rows)


def aggregate_dashboard(codes: list[str]) -> dict:
    df = score_batch(codes)
    if df.empty:
        return {"tier_distribution": {}, "top_failure_modes": []}
    tier_dist = df["credibility_tier"].value_counts().to_dict()
    fm_counts = {}
    for fms in df["failure_modes"]:
        for fm in fms or []:
            fm_counts[fm] = fm_counts.get(fm, 0) + 1
    top_fms = sorted(fm_counts.items(), key=lambda x: -x[1])[:5]
    return {
        "tier_distribution": tier_dist,
        "top_failure_modes": top_fms,
        "avg_methods_spread": df["methods_spread"].mean() if "methods_spread" in df.columns else 0,
    }
