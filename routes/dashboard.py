from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required

from models import FinancialData, LoanProduct, User, db
from utils.credit_score import evaluate_loan_eligibility
from utils.deepseek_client import generate_credit_analysis
from utils.loan_matcher import recommend_products_for_user

dashboard_bp = Blueprint("dashboard", __name__)


def _parse_bool_yes_no(v: Optional[str]) -> Optional[bool]:
    v = (v or "").strip().lower()
    if v == "yes":
        return True
    if v == "no":
        return False
    return None


def _parse_int_optional(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _parse_float_optional(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _parse_text_optional(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = str(v).strip()
    return v or None


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
        financial = FinancialData(user_id=user.id)
        db.session.add(financial)
        db.session.commit()

    industry_options = [
        "Commercial/Service",
        "Manufacturing",
        "Retail/Wholesale",
        "Wholesale",
        "Construction",
        "Transportation",
        "Professional Services",
        "Other",
    ]
    level_options = ["Very Good", "Good", "Average", "Poor", "Very Poor"]
    collateral_type_options = [
        "Property",
        "Deposit / Cash Collateral",
        "Accounts Receivable",
        "Vehicle",
        "Equipment",
        "Personal Guarantee Support",
        "Inventory",
        "Other",
    ]

    scoring_result: dict[str, Any] = {}

    if request.method == "POST":
        financial.annual_revenue = _parse_float_optional(request.form.get("annual_revenue"))
        financial.net_profit = _parse_float_optional(request.form.get("net_profit"))
        financial.has_bank_debt = _parse_bool_yes_no(request.form.get("has_bank_debt"))
        financial.has_collateral = _parse_bool_yes_no(request.form.get("has_collateral"))

        financial.industry_type = _parse_text_optional(request.form.get("industry_type"))
        financial.has_fixed_office = _parse_bool_yes_no(request.form.get("has_fixed_office"))
        financial.has_tax_records = _parse_bool_yes_no(request.form.get("has_tax_records"))

        financial.total_assets = _parse_int_optional(request.form.get("total_assets"))
        financial.total_liabilities = _parse_int_optional(request.form.get("total_liabilities"))
        financial.operating_cash_flow = _parse_float_optional(request.form.get("operating_cash_flow"))
        financial.revenue_growth_rate = _parse_float_optional(request.form.get("revenue_growth_rate"))

        financial.cash_flow_stability = _parse_text_optional(request.form.get("cash_flow_stability"))
        financial.overdue_count_last_12m = _parse_int_optional(request.form.get("overdue_count_last_12m"))
        financial.serious_default_flag = _parse_bool_yes_no(request.form.get("serious_default_flag"))
        financial.tax_abnormal_flag = _parse_bool_yes_no(request.form.get("tax_abnormal_flag"))
        financial.legal_risk_flag = _parse_bool_yes_no(request.form.get("legal_risk_flag"))

        financial.historical_repayment_quality = _parse_text_optional(request.form.get("historical_repayment_quality"))
        financial.collateral_type = _parse_text_optional(request.form.get("collateral_type"))
        financial.collateral_value = _parse_float_optional(request.form.get("collateral_value"))
        financial.guarantor_flag = _parse_bool_yes_no(request.form.get("guarantor_flag"))

        privacy_notice_accepted = bool(request.form.get("privacy_notice_accepted"))
        financial.privacy_notice_accepted_at = datetime.utcnow() if privacy_notice_accepted else None
        financial.consent_version = current_app.config.get("PRIVACY_CONSENT_VERSION")

        retention_days = current_app.config.get("DATA_RETENTION_DAYS")
        financial.data_retention_until = datetime.utcnow() if retention_days else None

        db.session.commit()

        scoring_result = evaluate_loan_eligibility(user, financial)
        user.credit_score = scoring_result.get("total_score", 0)
        user.credit_analysis = generate_credit_analysis(scoring_result)

        financial.scoring_version = scoring_result.get("engine_version")
        financial.scoring_updated_at = datetime.utcnow()
        db.session.commit()

        flash("Financial data updated. Eligibility and score recalculated (demo).", "success")

    if not scoring_result:
        scoring_result = evaluate_loan_eligibility(user, financial)
        user.credit_score = scoring_result.get("total_score", 0)
        if not user.credit_analysis:
            user.credit_analysis = generate_credit_analysis(scoring_result)
        db.session.commit()

    products = LoanProduct.query.order_by(LoanProduct.min_credit_score.desc()).all()
    product_matches = recommend_products_for_user(user, financial, scoring_result, products)

    recommended_products = [p for p in product_matches if p.get("eligible")]
    privacy_consent_version = current_app.config.get("PRIVACY_CONSENT_VERSION", "v1_default")

    return render_template(
        "dashboard.html",
        user=user,
        financial=financial,
        industry_options=industry_options,
        level_options=level_options,
        collateral_type_options=collateral_type_options,
        scoring=scoring_result,
        recommended_products=recommended_products,
        privacy_consent_version=privacy_consent_version,
    )


@dashboard_bp.route("/privacy", methods=["GET"])
def privacy():
    return render_template("privacy.html")

