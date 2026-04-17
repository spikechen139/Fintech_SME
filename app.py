from datetime import date
import os
import sqlite3

from flask import Flask, redirect, request, url_for
from flask_login import LoginManager, current_user

import config
from models import Appointment, LoanProduct, User, db
from routes.appointments import admin_bp, appointments_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please login to continue."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_today():
        return {"today_str": date.today().strftime("%Y-%m-%d")}

    @app.before_request
    def protect_routes():
        allowed_endpoints = {"auth.login", "auth.register", "dashboard.privacy", "static"}
        endpoint = request.endpoint or ""
        if endpoint in allowed_endpoints or endpoint.startswith("static"):
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        return None

    with app.app_context():
        db.create_all()
        apply_sqlite_schema_migrations()
        init_loan_products()

    return app


def _sqlite_db_path():
    uri = getattr(config, "SQLALCHEMY_DATABASE_URI", "")
    # Expected format: sqlite:////absolute/path/app.db
    if uri.startswith("sqlite:///"):
        return uri.replace("sqlite:///", "", 1)
    if uri.startswith("sqlite:"):
        return uri.replace("sqlite://", "", 1)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "app.db")


def _get_sqlite_columns(conn: sqlite3.Connection, table_name: str):
    cur = conn.execute(f"PRAGMA table_info({table_name});")
    return {row[1] for row in cur.fetchall()}  # row[1] is column name


def apply_sqlite_schema_migrations():
    """
    SQLite has no native schema migration in this project.
    We add missing columns with ALTER TABLE ADD COLUMN to keep app.db usable.
    """
    db_path = _sqlite_db_path()
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    try:
        # financial_data: add new scoring + privacy fields
        financial_cols = {
            "industry_type": "TEXT",
            "has_fixed_office": "INTEGER",
            "has_tax_records": "INTEGER",
            "revenue_growth_rate": "REAL",
            "total_assets": "INTEGER",
            "total_liabilities": "INTEGER",
            "operating_cash_flow": "REAL",
            "cash_flow_stability": "TEXT",
            "overdue_count_last_12m": "INTEGER",
            "serious_default_flag": "INTEGER",
            "tax_abnormal_flag": "INTEGER",
            "legal_risk_flag": "INTEGER",
            "historical_repayment_quality": "TEXT",
            "collateral_type": "TEXT",
            "collateral_value": "REAL",
            "guarantor_flag": "INTEGER",
            "collateral_coverage_ratio": "REAL",
            "consent_version": "TEXT",
            "privacy_notice_accepted_at": "TEXT",
            "data_retention_until": "TEXT",
            "scoring_updated_at": "TEXT",
            "scoring_version": "TEXT",
            # legacy compatibility
            "debt_service_amount": "REAL",
            "interest_expense": "REAL",
        }

        existing_financial = _get_sqlite_columns(conn, "financial_data")
        for col, typ in financial_cols.items():
            if col not in existing_financial:
                conn.execute(f"ALTER TABLE financial_data ADD COLUMN {col} {typ};")

        # loan_product: add new matching + disclosure fields
        loan_cols = {
            "allowed_risk_levels": "TEXT",
            "min_established_years": "INTEGER",
            "min_annual_revenue": "INTEGER",
            "require_collateral": "INTEGER",
            "allowed_industries": "TEXT",
            "max_debt_ratio": "REAL",
            "require_no_serious_default": "INTEGER",
            "compliance_note": "TEXT",
            "product_disclaimer": "TEXT",
        }
        existing_loan = _get_sqlite_columns(conn, "loan_product")
        for col, typ in loan_cols.items():
            if col not in existing_loan:
                conn.execute(f"ALTER TABLE loan_product ADD COLUMN {col} {typ};")

        conn.commit()
    finally:
        conn.close()


def init_loan_products():
    # Demo reset mode: clear existing product-related records, then recreate
    # the current 10 configured loan products on each startup.
    product_specs = [
        # Product 1: Original SME Flexi Loan (updated fields)
        {
            "name": "SME Flexi Loan",
            "bank_name": "HSBC",
            "min_credit_score": 80,
            "allowed_risk_levels": "A,B",
            "min_established_years": 5,
            "min_annual_revenue": 3000000,
            "require_collateral": True,
            "allowed_industries": "Commercial/Service,Manufacturing,Professional Services",
            "max_debt_ratio": 0.65,
            "require_no_serious_default": True,
            "max_amount": 5000000,
            "min_interest_rate": 5.5,
            "max_interest_rate": 8.5,
            "term_months": "12,24,36,48,60",
            "compliance_note": "Demo: eligibility uses user-submitted financial inputs only and is explainable (no ML/black box).",
            "product_disclaimer": "This is a demo recommendation for initial assessment. Final approval depends on the licensed institution/manual underwriting.",
        },
        # Product 2: Original SME Support Loan (updated fields)
        {
            "name": "SME Support Loan",
            "bank_name": "BOCHK",
            "min_credit_score": 60,
            "allowed_risk_levels": "B,C",
            "min_established_years": 3,
            "min_annual_revenue": 1500000,
            "require_collateral": False,
            "allowed_industries": "Commercial/Service,Retail/Wholesale,Professional Services",
            "max_debt_ratio": 0.75,
            "require_no_serious_default": True,
            "max_amount": 3000000,
            "min_interest_rate": 6.5,
            "max_interest_rate": 10.0,
            "term_months": "12,24,36,48",
            "compliance_note": "Demo: rule-based eligibility and conservative suggested amounts.",
            "product_disclaimer": "Not an official approval. Demo terms and rates are illustrative only.",
        },
        # Product 3: Original SME Instalment Loan (updated fields)
        {
            "name": "SME Instalment Loan",
            "bank_name": "ZA Bank",
            "min_credit_score": 40,
            "allowed_risk_levels": "C,D,E",
            "min_established_years": 1,
            "min_annual_revenue": 300000,
            "require_collateral": False,
            "allowed_industries": "Retail/Wholesale,Commercial/Service,Other",
            "max_debt_ratio": 0.85,
            "require_no_serious_default": False,
            "max_amount": 1000000,
            "min_interest_rate": 8.0,
            "max_interest_rate": 15.0,
            "term_months": "6,12,24,36",
            "compliance_note": "Demo: higher risk may receive conservative suggested amounts.",
            "product_disclaimer": "Demo recommendation only; final decision requires human review.",
        },
        # Product 4: Equipment/Vehicle secured
        {
            "name": "Equipment / Vehicle Secured Loan",
            "bank_name": "OCBC",
            "min_credit_score": 65,
            "allowed_risk_levels": "B,C",
            "min_established_years": 2,
            "min_annual_revenue": 1000000,
            "require_collateral": True,
            "allowed_industries": "Manufacturing,Transportation,Construction",
            "max_debt_ratio": 0.78,
            "require_no_serious_default": True,
            "max_amount": 2600000,
            "min_interest_rate": 6.2,
            "max_interest_rate": 10.2,
            "term_months": "12,24,36,48",
            "compliance_note": "Demo: collateral type mapping supports explainable scoring.",
            "product_disclaimer": "Illustrative terms only. Not an official lending commitment.",
        },
        # Product 5: Cashflow bridge (short term)
        {
            "name": "Cash Flow Bridge (Short-term)",
            "bank_name": "Hang Seng Bank",
            "min_credit_score": 60,
            "allowed_risk_levels": "B,C",
            "min_established_years": 2,
            "min_annual_revenue": 800000,
            "require_collateral": False,
            "allowed_industries": "Wholesale,Commercial/Service,Other",
            "max_debt_ratio": 0.80,
            "require_no_serious_default": True,
            "max_amount": 2000000,
            "min_interest_rate": 7.2,
            "max_interest_rate": 12.5,
            "term_months": "6,12",
            "compliance_note": "Demo: conservative limits based on operating cash flow.",
            "product_disclaimer": "Demo recommendation only; final approval by licensed institution.",
        },
        # Product 6: Inventory / trade-like
        {
            "name": "Trade & Inventory Financing (Demo)",
            "bank_name": "DBS",
            "min_credit_score": 55,
            "allowed_risk_levels": "C,D",
            "min_established_years": 2,
            "min_annual_revenue": 900000,
            "require_collateral": True,
            "allowed_industries": "Retail/Wholesale,Wholesale,Commercial/Service",
            "max_debt_ratio": 0.86,
            "require_no_serious_default": False,
            "max_amount": 2200000,
            "min_interest_rate": 7.8,
            "max_interest_rate": 13.8,
            "term_months": "6,12,24",
            "compliance_note": "Demo: explainable eligibility based on qualitative inputs.",
            "product_disclaimer": "Illustrative terms only; not an official approval.",
        },
        # Product 7: Growth / expansion
        {
            "name": "Growth Expansion Loan",
            "bank_name": "Standard Chartered",
            "min_credit_score": 75,
            "allowed_risk_levels": "A,B,C",
            "min_established_years": 3,
            "min_annual_revenue": 2500000,
            "require_collateral": False,
            "allowed_industries": "Manufacturing,Professional Services,Commercial/Service",
            "max_debt_ratio": 0.72,
            "require_no_serious_default": True,
            "max_amount": 4200000,
            "min_interest_rate": 6.0,
            "max_interest_rate": 9.2,
            "term_months": "12,24,36,48",
            "compliance_note": "Demo: recommended amount conservatively reflects growth and leverage.",
            "product_disclaimer": "Demo recommendation only; final underwriting required.",
        },
        # Product 8: Conservative small secured
        {
            "name": "Conservative Small Secured Loan",
            "bank_name": "Citi (Demo)",
            "min_credit_score": 50,
            "allowed_risk_levels": "C,D",
            "min_established_years": 1,
            "min_annual_revenue": 400000,
            "require_collateral": True,
            "allowed_industries": "Commercial/Service,Other",
            "max_debt_ratio": 0.88,
            "require_no_serious_default": False,
            "max_amount": 900000,
            "min_interest_rate": 8.5,
            "max_interest_rate": 15.5,
            "term_months": "6,12,24",
            "compliance_note": "Demo: collateral-driven conservative amount generation.",
            "product_disclaimer": "Not an official approval or lending commitment.",
        },
        # Product 9: Mature enterprise secured
        {
            "name": "Mature Enterprise Secured Loan (Demo)",
            "bank_name": "Bank of China (Demo)",
            "min_credit_score": 80,
            "allowed_risk_levels": "A,B",
            "min_established_years": 7,
            "min_annual_revenue": 3500000,
            "require_collateral": True,
            "allowed_industries": "Manufacturing,Wholesale,Professional Services",
            "max_debt_ratio": 0.60,
            "require_no_serious_default": True,
            "max_amount": 6000000,
            "min_interest_rate": 4.6,
            "max_interest_rate": 7.4,
            "term_months": "12,24,36,48,60",
            "compliance_note": "Demo: higher thresholds for stable, mature businesses.",
            "product_disclaimer": "Illustrative only; final decision by licensed institution/manual underwriting.",
        },
        # Product 10: Unsecured SME general
        {
            "name": "Unsecured SME General Loan",
            "bank_name": "Regional Bank (Demo)",
            "min_credit_score": 55,
            "allowed_risk_levels": "C,D,E",
            "min_established_years": 2,
            "min_annual_revenue": 700000,
            "require_collateral": False,
            "allowed_industries": "Commercial/Service,Retail/Wholesale,Other",
            "max_debt_ratio": 0.82,
            "require_no_serious_default": False,
            "max_amount": 1500000,
            "min_interest_rate": 8.8,
            "max_interest_rate": 15.0,
            "term_months": "12,24,36",
            "compliance_note": "Demo: unsecured products are more conservative on suggested amounts.",
            "product_disclaimer": "Demo recommendation only. Terms shown are illustrative.",
        },
    ]

    # Appointment rows reference loan products. For this demo reset behavior,
    # we clear appointments first so product IDs can be recreated cleanly.
    Appointment.query.delete()
    LoanProduct.query.delete()

    for spec in product_specs:
        product = LoanProduct(**spec)
        db.session.add(product)

    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
