from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


LEVEL_SCORE_MAP = {
    "Very Good": 4,
    "Good": 3,
    "Average": 2,
    "Poor": 1,
    "Very Poor": 0,
}

REPAYMENT_LEVEL_SCORE_MAP = {
    "Very Good": 4,
    "Good": 3,
    "Average": 2,
    "Poor": 1,
    "Very Poor": 0,
}

COLLATERAL_TYPE_SCORE_MAP = {
    "Property": 2,
    "Deposit / Cash Collateral": 2,
    "Accounts Receivable": 2,
    "Vehicle": 1,
    "Equipment": 1,
    "Personal Guarantee Support": 1,
    "Inventory": 0,
    "Other": 0,
}


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        n = float(v)
    except Exception:
        return None
    if n != n:  # NaN
        return None
    return n


def _safe_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _risk_level_from_score(total_score: int) -> str:
    if 85 <= total_score <= 100:
        return "A"
    if 70 <= total_score <= 84:
        return "B"
    if 55 <= total_score <= 69:
        return "C"
    if 40 <= total_score <= 54:
        return "D"
    return "E"


def _penalty(code: str, points: int, description: str) -> Dict[str, Any]:
    return {"code": code, "points": points, "description": description}


def _compute_dim_scores(user: Any, financial: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (dimension_scores, penalties, extras).
    """
    # -------- Selected qualitative inputs (for explainability) --------
    cash_flow_stability = getattr(financial, "cash_flow_stability", None)
    historical_repayment_quality = getattr(financial, "historical_repayment_quality", None)
    collateral_type = getattr(financial, "collateral_type", None)

    # -------- Numerical inputs --------
    established_years = _safe_int(getattr(user, "established_year", None)) or 0

    annual_revenue = _safe_float(getattr(financial, "annual_revenue", None)) or 0.0
    net_profit = _safe_float(getattr(financial, "net_profit", None)) or 0.0

    has_bank_debt = bool(getattr(financial, "has_bank_debt", False))
    total_assets = _safe_float(getattr(financial, "total_assets", None)) or 0.0
    total_liabilities = _safe_float(getattr(financial, "total_liabilities", None)) or 0.0

    operating_cash_flow = _safe_float(getattr(financial, "operating_cash_flow", None)) or 0.0
    overdue_count_last_12m = _safe_int(getattr(financial, "overdue_count_last_12m", None)) or 0

    serious_default_flag = bool(getattr(financial, "serious_default_flag", False))
    tax_abnormal_flag = bool(getattr(financial, "tax_abnormal_flag", False))
    legal_risk_flag = bool(getattr(financial, "legal_risk_flag", False))

    has_collateral = bool(getattr(financial, "has_collateral", False))
    collateral_value = _safe_float(getattr(financial, "collateral_value", None)) or 0.0
    guarantor_flag = bool(getattr(financial, "guarantor_flag", False))
    collateral_coverage_ratio = _safe_float(getattr(financial, "collateral_coverage_ratio", None))

    # -------- Derived ratios --------
    debt_ratio = None
    if total_assets > 0:
        debt_ratio = float(total_liabilities) / float(total_assets)
    else:
        debt_ratio = None

    cf_ratio = None
    if total_liabilities > 0:
        cf_ratio = operating_cash_flow / (total_liabilities + 1.0)

    # =====================
    # Dimension A (15)
    # =====================
    industry_type = getattr(financial, "industry_type", None) or ""
    has_fixed_office = bool(getattr(financial, "has_fixed_office", False))
    has_tax_records = bool(getattr(financial, "has_tax_records", False))

    # years portion (<= 10) then cap to 15 with other parts
    if established_years >= 8:
        years_score = 10
    elif established_years >= 5:
        years_score = 8
    elif established_years >= 3:
        years_score = 6
    elif established_years >= 1:
        years_score = 3
    else:
        years_score = 0

    industry_score = 3 if industry_type else 0
    fixed_office_score = 1 if has_fixed_office else 0
    tax_records_score = 1 if has_tax_records else 0

    dim_A = int(_clamp(years_score + industry_score + fixed_office_score + tax_records_score, 0, 15))

    # =====================
    # Dimension B (20)
    # =====================
    # revenue score (0..8)
    if annual_revenue >= 10_000_000:
        revenue_score = 8
    elif annual_revenue >= 5_000_000:
        revenue_score = 6
    elif annual_revenue >= 1_000_000:
        revenue_score = 4
    else:
        revenue_score = 1 if annual_revenue > 0 else 0

    # profit score (0..6)
    profit_score = 6 if net_profit > 0 else 0

    # margin score (0..4)
    margin_score = 0
    if annual_revenue > 0:
        margin = net_profit / annual_revenue
        if margin >= 0.20:
            margin_score = 4
        elif margin >= 0.10:
            margin_score = 3
        elif margin >= 0.05:
            margin_score = 2
        elif margin >= 0.00:
            margin_score = 1
        else:
            margin_score = 0

    # growth score (0..2)
    growth_rate = _safe_float(getattr(financial, "revenue_growth_rate", None))
    growth_score = 0
    if growth_rate is not None:
        if growth_rate >= 0.10:
            growth_score = 2
        elif growth_rate >= 0.00:
            growth_score = 1
        else:
            growth_score = 0

    dim_B = int(_clamp(revenue_score + profit_score + margin_score + growth_score, 0, 20))

    # =====================
    # Dimension C (25)
    # =====================
    assets_score = 0
    if total_assets >= 50_000_000:
        assets_score = 5
    elif total_assets >= 10_000_000:
        assets_score = 3
    elif total_assets >= 1_000_000:
        assets_score = 1

    debt_ratio_score = 0
    if debt_ratio is not None:
        if debt_ratio <= 0.30:
            debt_ratio_score = 12
        elif debt_ratio <= 0.50:
            debt_ratio_score = 9
        elif debt_ratio <= 0.70:
            debt_ratio_score = 6
        else:
            debt_ratio_score = 2

    bank_debt_score = 0
    if has_bank_debt:
        if debt_ratio is not None and debt_ratio <= 0.60:
            bank_debt_score = 3
        else:
            bank_debt_score = 1

    dim_C = int(_clamp(assets_score + debt_ratio_score + bank_debt_score, 0, 25))

    # =====================
    # Dimension D (20)
    # =====================
    # cash flow base (0..8)
    if operating_cash_flow >= 5_000_000:
        cf_base_score = 8
    elif operating_cash_flow >= 1_000_000:
        cf_base_score = 6
    elif operating_cash_flow >= 0:
        cf_base_score = 3
    else:
        cf_base_score = 0

    cf_stability_score = LEVEL_SCORE_MAP.get(str(cash_flow_stability), 0)  # 0..4
    cf_stability_score = int(cf_stability_score * 2)  # 0..8

    cf_to_liab_score = 0
    if cf_ratio is not None:
        if cf_ratio >= 1.0:
            cf_to_liab_score = 4
        elif cf_ratio >= 0.5:
            cf_to_liab_score = 3
        elif cf_ratio >= 0.2:
            cf_to_liab_score = 2
        else:
            cf_to_liab_score = 0

    dim_D = int(_clamp(cf_base_score + cf_stability_score + cf_to_liab_score, 0, 20))

    # =====================
    # Dimension E (10)
    # =====================
    # Overdue component (0..6)
    if overdue_count_last_12m <= 0:
        overdue_score = 6
    elif overdue_count_last_12m == 1:
        overdue_score = 4
    elif overdue_count_last_12m == 2:
        overdue_score = 2
    else:
        overdue_score = 0

    repayment_quality_score = int(REPAYMENT_LEVEL_SCORE_MAP.get(str(historical_repayment_quality), 0))  # 0..4
    dim_E = int(_clamp(overdue_score + repayment_quality_score, 0, 10))

    # =====================
    # Dimension F (10)
    # =====================
    collateral_presence_score = 4 if has_collateral else 0
    collateral_type_score = int(COLLATERAL_TYPE_SCORE_MAP.get(str(collateral_type), 0)) * 1  # 0..2
    collateral_value_score = 0
    if collateral_value >= 10_000_000:
        collateral_value_score = 2
    elif collateral_value >= 3_000_000:
        collateral_value_score = 1

    guarantor_score = 2 if guarantor_flag else 0

    coverage_score = 0
    if collateral_coverage_ratio is not None:
        if float(collateral_coverage_ratio) >= 1.5:
            coverage_score = 2
        elif float(collateral_coverage_ratio) >= 1.0:
            coverage_score = 1
        else:
            coverage_score = 0
    else:
        # fallback: use debt_ratio as proxy
        if debt_ratio is not None and debt_ratio <= 0.5:
            coverage_score = 1

    # Ensure total <= 10
    dim_F = int(_clamp(collateral_presence_score + collateral_type_score + collateral_value_score + guarantor_score + coverage_score, 0, 10))

    # =====================
    # Penalties (deduct from total score)
    # =====================
    penalties: List[Dict[str, Any]] = []

    if overdue_count_last_12m >= 3:
        penalties.append(_penalty("OVERDUE_12M_SEVERE", 8, "Multiple overdue records in the last 12 months indicate elevated credit behavior risk."))
    elif overdue_count_last_12m >= 1:
        penalties.append(_penalty("OVERDUE_12M", 4, "Minor overdue records in the last 12 months lead to a credit behavior deduction."))

    if str(cash_flow_stability) in {"Poor", "Very Poor"}:
        penalties.append(_penalty("CASHFLOW_STABILITY_LOW", 4, "Operating cash flow stability is weak, resulting in a deduction."))

    if debt_ratio is not None and debt_ratio > 0.70:
        penalties.append(_penalty("LEVERAGE_HIGH", 5, "Debt ratio is high, indicating potentially heavy repayment pressure."))

    if tax_abnormal_flag:
        penalties.append(_penalty("TAX_ABNORMAL", 4, "Tax/reporting abnormality flag triggers a deduction and may require manual review."))

    if legal_risk_flag:
        penalties.append(_penalty("LEGAL_RISK", 4, "Legal/dispute risk flag triggers a deduction and may require manual review."))

    if serious_default_flag:
        penalties.append(_penalty("SERIOUS_DEFAULT", 15, "Serious default risk flag causes a significant deduction and may lead to rejection."))

    dimension_scores = {
        "A": {"dimension": "A", "title": "Enterprise Fundamentals", "score": dim_A, "max": 15},
        "B": {"dimension": "B", "title": "Profitability", "score": dim_B, "max": 20},
        "C": {"dimension": "C", "title": "Debt Repayment Capacity", "score": dim_C, "max": 25},
        "D": {"dimension": "D", "title": "Cash Flow Capacity", "score": dim_D, "max": 20},
        "E": {"dimension": "E", "title": "Credit History & Behavior", "score": dim_E, "max": 10},
        "F": {"dimension": "F", "title": "Credit Enhancement", "score": dim_F, "max": 10},
    }

    extra = {
        "selected_levels": {
            "cash_flow_stability": cash_flow_stability,
            "historical_repayment_quality": historical_repayment_quality,
            "collateral_type": collateral_type,
        },
        "computed_metrics": {
            "debt_ratio": debt_ratio,
            "cash_flow_to_liabilities_ratio": cf_ratio,
            "overdue_count_last_12m": overdue_count_last_12m,
        },
        "level_impact_summary": [
            f"Cash flow stability: {cash_flow_stability or 'Not provided'}",
            f"Historical repayment quality: {historical_repayment_quality or 'Not provided'}",
            f"Collateral type: {collateral_type or 'Not provided'}",
        ],
        "eligibility_flags": {
            "serious_default_flag": serious_default_flag,
            "tax_abnormal_flag": tax_abnormal_flag,
            "legal_risk_flag": legal_risk_flag,
            "overdue_count_last_12m": overdue_count_last_12m,
        },
    }

    return dimension_scores, penalties, extra


def evaluate_loan_eligibility(user: Any, financial: Any) -> Dict[str, Any]:
    """
    Explainable rule-based eligibility and 100-point scoring model.
    Demo-only: never auto-approve; used for initial assessment.
    """
    dimension_scores, penalties, extra = _compute_dim_scores(user, financial)
    penalties_points = sum(int(p.get("points", 0) or 0) for p in penalties)
    dim_sum = sum(int(d["score"]) for d in dimension_scores.values())
    total_score = int(_clamp(dim_sum - penalties_points, 0, 100))
    risk_level = _risk_level_from_score(total_score)

    # ---------------------
    # Eligibility screening
    # ---------------------
    flags = extra["eligibility_flags"]
    serious_default_flag = bool(flags.get("serious_default_flag"))
    legal_risk_flag = bool(flags.get("legal_risk_flag"))
    tax_abnormal_flag = bool(flags.get("tax_abnormal_flag"))
    overdue_count_last_12m = int(flags.get("overdue_count_last_12m") or 0)

    # Missing data check (demo only)
    missing: List[str] = []
    for field in [
        "annual_revenue",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "operating_cash_flow",
        "cash_flow_stability",
        "overdue_count_last_12m",
        "historical_repayment_quality",
        "collateral_type",
        "collateral_value",
        "guarantor_flag",
    ]:
        val = getattr(financial, field, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    reject_reasons: List[str] = []
    manual_review_reasons: List[str] = []

    if serious_default_flag:
        reject_reasons.append("Serious default risk flag detected: this demo does not recommend proceeding to product matching.")
        eligibility_status = "rejected"
    elif overdue_count_last_12m >= 5:
        reject_reasons.append("Overdue count in the last 12 months is high: credit behavior risk is significant.")
        eligibility_status = "rejected"
    else:
        # Manual review
        if missing:
            manual_review_reasons.append(f"Substantial missing data (demo): please provide additional fields: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}.")
        if legal_risk_flag:
            manual_review_reasons.append("Legal/dispute risk flag detected: manual review is required.")
        if tax_abnormal_flag:
            manual_review_reasons.append("Tax/reporting abnormality flag detected: manual review is required.")

        eligibility_status = "eligible" if not manual_review_reasons else "manual_review"

    risk_summary = f"Total score {total_score}/100, corresponding to risk level {risk_level} (demo)."
    underwriting_note = (
        "This system is for initial assessment and product matching reference only. It does not constitute automatic approval or legal commitment. Final decisions must be made by licensed institutions or manual underwriting."
    )

    scoring_result: Dict[str, Any] = {
        "eligibility_status": eligibility_status,
        "reject_reasons": reject_reasons,
        "manual_review_reasons": manual_review_reasons,
        "dimension_scores": dimension_scores,
        "penalties": penalties,
        "total_score": total_score,
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "underwriting_note": underwriting_note,
        "selected_levels": extra["selected_levels"],
        "level_impact_summary": extra["level_impact_summary"],
        # optional for templates/extendability
        "fairness_checks": [
            "Protected attributes are excluded: scoring does not use gender / race / disability or similar attributes (demo)."
        ],
        "privacy_checks": [
            "AI explanation uses only anonymized scoring summaries, not full personal data (demo)."
        ],
        "engine_version": "demo_rule_engine_v1",
    }

    return scoring_result


def calculate_credit_score(user_id: int) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for the old route code.
    Prefer evaluate_loan_eligibility in new UI.
    """
    # Lazy import to avoid circular deps
    from models import FinancialData, User  # noqa

    user = User.query.get(user_id)
    if not user:
        return {"total_score": 0, "risk_level": "E", "eligibility_status": "manual_review", "dimension_scores": {}, "penalties": []}

    financial = FinancialData.query.filter_by(user_id=user.id).first()
    if not financial:
        financial = FinancialData(user_id=user.id)

    scoring = evaluate_loan_eligibility(user, financial)

    user.credit_score = scoring["total_score"]
    return scoring

