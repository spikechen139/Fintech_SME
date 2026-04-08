from datetime import date

from models import FinancialData, User, db


def calculate_credit_score(user_id):
    user = User.query.get(user_id)
    if not user:
        return {"total": 0, "years": 0, "revenue": 0, "profit": 0, "debt": 0, "collateral": 0}

    financial = FinancialData.query.filter_by(user_id=user_id).first()
    if not financial:
        financial = FinancialData(
            user_id=user_id,
            annual_revenue=0,
            net_profit=0,
            has_bank_debt=True,
            has_collateral=False,
        )
        db.session.add(financial)
        db.session.flush()

    current_year = date.today().year
    years_since_established = max(0, current_year - user.established_year)

    if years_since_established >= 5:
        years_score = 20
    elif years_since_established >= 3:
        years_score = 15
    elif years_since_established >= 1:
        years_score = 8
    else:
        years_score = 0

    annual_revenue = financial.annual_revenue or 0
    if annual_revenue >= 10_000_000:
        revenue_score = 30
    elif annual_revenue >= 5_000_000:
        revenue_score = 20
    elif annual_revenue >= 1_000_000:
        revenue_score = 10
    else:
        revenue_score = 0

    net_profit = financial.net_profit or 0
    profit_score = 20 if net_profit > 0 else 0

    has_bank_debt = True if financial.has_bank_debt is None else financial.has_bank_debt
    debt_score = 5 if has_bank_debt else 15

    has_collateral = bool(financial.has_collateral)
    collateral_score = 10 if has_collateral else 0

    total_score = years_score + revenue_score + profit_score + debt_score + collateral_score
    user.credit_score = total_score
    db.session.commit()

    return {
        "total": total_score,
        "years": years_score,
        "revenue": revenue_score,
        "profit": profit_score,
        "debt": debt_score,
        "collateral": collateral_score,
    }
