import requests
from flask import current_app


FALLBACK_ANALYSIS = (
    "Your credit profile is acceptable. To improve your score, "
    "consider increasing revenue or reducing debt."
)


def generate_credit_analysis(scoring_result):
    """
    Demo-friendly explainability layer.
    Important: Only send minimal, derived scoring outputs to the external model (no raw personal data).
    """
    if not isinstance(scoring_result, dict):
        scoring_result = {}

    total_score = scoring_result.get("total_score", 0) or 0
    risk_level = scoring_result.get("risk_level", "E") or "E"
    eligibility = scoring_result.get("eligibility_status", "manual_review") or "manual_review"

    # Dimension summary for explainability
    dim_scores = scoring_result.get("dimension_scores", {}) or {}
    dim_summary = []
    for k in ["A", "B", "C", "D", "E", "F"]:
        d = dim_scores.get(k) if isinstance(dim_scores, dict) else None
        if d:
            dim_summary.append(f"{d.get('title','')}: {d.get('score',0)}/{d.get('max',0)}")

    penalties = scoring_result.get("penalties", []) or []
    penalty_codes = [p.get("code") for p in penalties if isinstance(p, dict) and p.get("code")]
    manual_reasons = scoring_result.get("manual_review_reasons", []) or []
    reject_reasons = scoring_result.get("reject_reasons", []) or []

    prompt = (
        "You are a fintech risk explainability assistant for a credit scoring demo.\n"
        "Write in a neutral, professional tone.\n"
        "Do NOT promise approval; state that this is for initial assessment only.\n"
        "Keep it under 140 words.\n\n"
        f"Total score: {total_score}/100\n"
        f"Risk level: {risk_level}\n"
        f"Eligibility status: {eligibility}\n"
        f"Dimension summary: {', '.join(dim_summary) if dim_summary else 'N/A'}\n"
        f"Penalty codes: {', '.join(penalty_codes) if penalty_codes else 'None'}\n"
        f"Manual review reasons: {manual_reasons[:3]}\n"
        f"Reject reasons: {reject_reasons[:3]}\n"
        "Output: 1) one-sentence interpretation, 2) two improvement suggestions."
    )

    headers = {
        "Authorization": f"Bearer {current_app.config['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": current_app.config["DEEPSEEK_MODEL"],
        "messages": [
            {"role": "system", "content": "You are a helpful financial advisor."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        response = requests.post(
            current_app.config["DEEPSEEK_API_URL"],
            headers=headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return FALLBACK_ANALYSIS
