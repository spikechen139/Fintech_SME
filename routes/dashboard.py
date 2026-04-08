from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import FinancialData, LoanProduct, User, db
from utils.credit_score import calculate_credit_score
from utils.deepseek_client import generate_credit_analysis

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user = User.query.get(current_user.id)
    financial = FinancialData.query.filter_by(user_id=user.id).first()
    if not financial:
        financial = FinancialData(
            user_id=user.id,
            annual_revenue=0,
            net_profit=0,
            has_bank_debt=True,
            has_collateral=False,
        )
        db.session.add(financial)
        db.session.commit()

    score_breakdown = {
        "total": user.credit_score or 0,
        "years": 0,
        "revenue": 0,
        "profit": 0,
        "debt": 0,
        "collateral": 0,
    }

    if request.method == "POST":
        try:
            annual_revenue = int(request.form.get("annual_revenue", 0))
            net_profit = int(request.form.get("net_profit", 0))
            has_bank_debt = request.form.get("has_bank_debt", "yes") == "yes"
            has_collateral = request.form.get("has_collateral", "no") == "yes"
        except ValueError:
            flash("Revenue and net profit must be integer values.", "danger")
            return redirect(url_for("dashboard.dashboard"))

        financial.annual_revenue = annual_revenue
        financial.net_profit = net_profit
        financial.has_bank_debt = has_bank_debt
        financial.has_collateral = has_collateral
        db.session.commit()

        score_breakdown = calculate_credit_score(user.id)
        user.credit_analysis = generate_credit_analysis(score_breakdown)
        db.session.commit()
        flash("Financial data updated. Credit score recalculated.", "success")
    else:
        score_breakdown = calculate_credit_score(user.id)
        if not user.credit_analysis:
            user.credit_analysis = generate_credit_analysis(score_breakdown)
            db.session.commit()

    products = (
        LoanProduct.query.filter(LoanProduct.min_credit_score <= (user.credit_score or 0))
        .order_by(LoanProduct.min_credit_score.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        user=user,
        financial=financial,
        score_breakdown=score_breakdown,
        products=products,
    )


@dashboard_bp.route("/privacy", methods=["GET"])
def privacy():
    return render_template("privacy.html")
