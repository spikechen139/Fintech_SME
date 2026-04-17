from __future__ import annotations

from typing import Any, Dict, List, Optional


def _parse_allowed_levels(s: Optional[str]) -> List[str]:
    if not s:
        return []
    # allow comma or whitespace separated values
    return [x.strip() for x in s.replace(" ", "").split(",") if x.strip()]


def _parse_allowed_industries(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _risk_factor(risk_level: str) -> float:
    # More conservative for higher risk levels
    return {
        "A": 0.95,
        "B": 0.85,
        "C": 0.75,
        "D": 0.65,
        "E": 0.55,
    }.get(risk_level, 0.6)


def _suggest_amount(product: Any, financial: Any, scoring_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate conservative suggested amount based on multiple caps.
    This is demo-only and must remain conservative.
    """
    annual_revenue = getattr(financial, "annual_revenue", None)
    net_profit = getattr(financial, "net_profit", None)
    operating_cash_flow = getattr(financial, "operating_cash_flow", None)
    has_collateral = bool(getattr(financial, "has_collateral", False))
    collateral_value = getattr(financial, "collateral_value", None)

    caps: List[float] = []
    reasons: List[str] = []

    if isinstance(annual_revenue, (int, float)) and annual_revenue >= 0:
        caps.append(annual_revenue * 0.12)
        reasons.append("12% of annual revenue is used as a conservative cap.")

    if isinstance(net_profit, (int, float)) and net_profit > 0:
        caps.append(net_profit * 3.0)
        reasons.append("3x annual net profit is used as a conservative cap.")

    if isinstance(operating_cash_flow, (int, float)) and operating_cash_flow > 0:
        caps.append(operating_cash_flow * 2.0)
        reasons.append("2x operating cash flow is used as a cap.")

    if has_collateral and isinstance(collateral_value, (int, float)) and collateral_value > 0:
        caps.append(collateral_value * 0.60)
        reasons.append("60% of collateral value is used as a cap.")

    total_score = float(scoring_result.get("total_score", 0) or 0)
    risk_level = scoring_result.get("risk_level", "E") or "E"
    rf = _risk_factor(risk_level)

    if not caps:
        # Data insufficient -> conservative/manual review amount
        conservative = 0
        return {
            "recommended_amount": conservative,
            "suggested_amount_range": {"low": conservative, "high": conservative},
            "amount_reasons": ["Insufficient data: unable to generate a conservative amount (demo). Please provide more financial inputs and reassess."],
        }

    raw = min(caps) * rf
    max_amount = getattr(product, "max_amount", None)
    if isinstance(max_amount, (int, float)) and max_amount > 0:
        raw = min(raw, float(max_amount))

    # Ensure non-negative & integer-ish (HKD)
    recommended = max(0, int(raw))

    # Range around recommended amount (conservative band)
    low = int(recommended * 0.8)
    high = int(max(recommended, recommended * 1.05))
    return {
        "recommended_amount": recommended,
        "suggested_amount_range": {"low": low, "high": high},
        "amount_reasons": reasons + [f"Conservative risk-level adjustment applied for level {risk_level} (factor {rf})."],
    }


def recommend_products_for_user(
    user: Any,
    financial: Any,
    scoring_result: Dict[str, Any],
    products: List[Any],
) -> List[Dict[str, Any]]:
    """
    Multi-conditional product eligibility & display model.
    Returns list of dicts suitable for templates/dashboard.html.
    """
    total_score = int(scoring_result.get("total_score", 0) or 0)
    risk_level = scoring_result.get("risk_level", "E") or "E"

    recs: List[Dict[str, Any]] = []

    for product in products:
        match_reasons: List[str] = []
        failed_reasons: List[str] = []

        # condition checks (all demo-only / explainable)
        ok = True

        if total_score < int(getattr(product, "min_credit_score", 0) or 0):
            ok = False
            failed_reasons.append("Credit score below the product minimum threshold.")
        else:
            match_reasons.append("Credit score meets the product minimum requirement.")

        allowed_risks = _parse_allowed_levels(getattr(product, "allowed_risk_levels", None))
        if allowed_risks and risk_level not in allowed_risks:
            ok = False
            failed_reasons.append("Risk level mismatch: not within the product's allowed risk levels.")
        elif allowed_risks:
            match_reasons.append("Risk level matches the product target segment.")

        established_years = getattr(user, "established_year", None)
        min_years = getattr(product, "min_established_years", None)
        if isinstance(min_years, int) and min_years > 0:
            if not isinstance(established_years, int):
                ok = False
                failed_reasons.append("Missing business age data: unable to verify the minimum operating years requirement.")
            elif established_years < min_years:
                ok = False
                failed_reasons.append("Insufficient operating years: below the product minimum.")
            else:
                match_reasons.append("Operating years meet the product threshold.")

        annual_revenue = getattr(financial, "annual_revenue", None)
        min_rev = getattr(product, "min_annual_revenue", None)
        if isinstance(min_rev, int) and min_rev > 0:
            if not isinstance(annual_revenue, (int, float)) or annual_revenue < min_rev:
                ok = False
                failed_reasons.append("Annual revenue below the product minimum threshold.")
            else:
                match_reasons.append("Annual revenue meets the product threshold.")

        require_collateral = bool(getattr(product, "require_collateral", False))
        has_collateral = bool(getattr(financial, "has_collateral", False))
        collateral_value = getattr(financial, "collateral_value", None)
        if require_collateral:
            if not has_collateral:
                ok = False
                failed_reasons.append("This product requires collateral support, but no collateral is provided.")
            elif not isinstance(collateral_value, (int, float)) or collateral_value <= 0:
                ok = False
                failed_reasons.append("Invalid collateral valuation: a value greater than 0 is required (demo).")
            else:
                match_reasons.append("Collateral requirement is satisfied.")

        allowed_industries = _parse_allowed_industries(getattr(product, "allowed_industries", None))
        industry_type = getattr(financial, "industry_type", None)
        if allowed_industries:
            if not industry_type or industry_type not in allowed_industries:
                ok = False
                failed_reasons.append("Industry is outside this product's supported range (demo).")
            else:
                match_reasons.append("Industry type matches the product target segment.")

        # debt ratio gate (if product provides max)
        max_debt_ratio = getattr(product, "max_debt_ratio", None)
        if isinstance(max_debt_ratio, (int, float)) and max_debt_ratio > 0:
            total_assets = getattr(financial, "total_assets", None)
            total_liabilities = getattr(financial, "total_liabilities", None)
            if isinstance(total_assets, (int, float)) and total_assets > 0 and isinstance(total_liabilities, (int, float)):
                debt_ratio = float(total_liabilities) / float(total_assets)
                if debt_ratio > float(max_debt_ratio):
                    ok = False
                    failed_reasons.append("Debt ratio is too high: exceeds the product maximum debt ratio.")
                else:
                    match_reasons.append("Debt ratio is within acceptable range.")
            else:
                ok = False
                failed_reasons.append("Insufficient balance-sheet data: unable to verify debt ratio threshold (demo).")

        # default gate
        require_no_serious_default = bool(getattr(product, "require_no_serious_default", False))
        serious_default_flag = bool(getattr(financial, "serious_default_flag", False))
        if require_no_serious_default and serious_default_flag:
            ok = False
            failed_reasons.append("Serious default risk flag detected: this product requires no serious default.")
        elif require_no_serious_default:
            match_reasons.append("No serious default risk flag (requirement satisfied).")

        # eligibility result
        eligible = ok

        amount = _suggest_amount(product, financial, scoring_result)

        # Display model
        recs.append(
            {
                "product_id": product.id,
                "product_name": getattr(product, "name", ""),
                "bank_name": getattr(product, "bank_name", ""),
                "eligible": eligible,
                "min_credit_score": getattr(product, "min_credit_score", None),
                "min_interest_rate": getattr(product, "min_interest_rate", None),
                "max_interest_rate": getattr(product, "max_interest_rate", None),
                "allowed_risk_levels": getattr(product, "allowed_risk_levels", None),
                "min_established_years": getattr(product, "min_established_years", None),
                "min_annual_revenue": getattr(product, "min_annual_revenue", None),
                "require_collateral": getattr(product, "require_collateral", None),
                "allowed_industries": getattr(product, "allowed_industries", None),
                "max_debt_ratio": getattr(product, "max_debt_ratio", None),
                "max_amount": getattr(product, "max_amount", None),
                "interest_range": f"{getattr(product, 'min_interest_rate', '')}% - {getattr(product, 'max_interest_rate', '')}%",
                "term_options": getattr(product, "term_months", ""),
                "suggested_amount_range": amount["suggested_amount_range"],
                "recommended_amount": amount["recommended_amount"],
                "compliance_note": getattr(product, "compliance_note", ""),
                "product_disclaimer": getattr(product, "product_disclaimer", ""),
                "match_reasons": match_reasons,
                "failed_reasons": failed_reasons,
            }
        )

    return recs

