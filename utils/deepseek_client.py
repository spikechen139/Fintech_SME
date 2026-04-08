import requests
from flask import current_app


FALLBACK_ANALYSIS = (
    "Your credit profile is acceptable. To improve your score, "
    "consider increasing revenue or reducing debt."
)


def generate_credit_analysis(score_breakdown):
    score = score_breakdown.get("total", 0)
    years_score = score_breakdown.get("years", 0)
    revenue_score = score_breakdown.get("revenue", 0)
    profit_score = score_breakdown.get("profit", 0)
    debt_score = score_breakdown.get("debt", 0)
    collateral_score = score_breakdown.get("collateral", 0)

    prompt = f"""You are a financial advisor. Based on the following credit score factors (max 100), generate a short professional analysis (max 150 words) in English. Include: a brief interpretation of the score, and two specific suggestions to improve the score.
- Credit score: {score}
- Years score: {years_score}/20
- Revenue score: {revenue_score}/30
- Profit score: {profit_score}/20
- Debt score: {debt_score}/15
- Collateral score: {collateral_score}/10
"""

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
