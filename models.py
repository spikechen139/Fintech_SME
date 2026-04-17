from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    br_number = db.Column(db.String(50), nullable=False)
    established_year = db.Column(db.Integer, nullable=False)

    # Scoring outputs (demo only)
    credit_score = db.Column(db.Integer, default=0)
    credit_analysis = db.Column(db.Text, default="")

    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    financial_data = db.relationship("FinancialData", backref="user", uselist=False)
    appointments = db.relationship("Appointment", backref="user", lazy=True)


class FinancialData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)

    # Core required inputs (from your form)
    annual_revenue = db.Column(db.Float)
    net_profit = db.Column(db.Float)
    has_bank_debt = db.Column(db.Boolean)
    has_collateral = db.Column(db.Boolean)

    # Enterprise / operating quality
    industry_type = db.Column(db.String(50))
    has_fixed_office = db.Column(db.Boolean)
    has_tax_records = db.Column(db.Boolean)
    revenue_growth_rate = db.Column(db.Float)

    # Balance sheet / leverage
    total_assets = db.Column(db.Integer)
    total_liabilities = db.Column(db.Integer)
    operating_cash_flow = db.Column(db.Float)

    # Categorical qualitative indicators (mapped to demo scores)
    cash_flow_stability = db.Column(db.String(20))
    overdue_count_last_12m = db.Column(db.Integer)

    # Adverse / risk flags (used only for demo screening)
    serious_default_flag = db.Column(db.Boolean)
    tax_abnormal_flag = db.Column(db.Boolean)
    legal_risk_flag = db.Column(db.Boolean)
    historical_repayment_quality = db.Column(db.String(20))

    # Credit enhancement
    collateral_type = db.Column(db.String(50))
    collateral_value = db.Column(db.Float)
    guarantor_flag = db.Column(db.Boolean)
    collateral_coverage_ratio = db.Column(db.Float)

    # Privacy / compliance metadata (demo only)
    consent_version = db.Column(db.String(50))
    privacy_notice_accepted_at = db.Column(db.DateTime)
    data_retention_until = db.Column(db.DateTime)
    scoring_updated_at = db.Column(db.DateTime)
    scoring_version = db.Column(db.String(50))

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Legacy columns intentionally not used by the new scoring engine.
    debt_service_amount = db.Column(db.Float)
    interest_expense = db.Column(db.Float)


class LoanProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Product identity
    name = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)

    # Basic thresholds / demo matching
    min_credit_score = db.Column(db.Integer, nullable=False)
    allowed_risk_levels = db.Column(db.String(20))
    min_established_years = db.Column(db.Integer)
    min_annual_revenue = db.Column(db.Integer)

    require_collateral = db.Column(db.Boolean)
    allowed_industries = db.Column(db.String(200))
    max_debt_ratio = db.Column(db.Float)
    require_no_serious_default = db.Column(db.Boolean)

    # Product pricing / terms
    max_amount = db.Column(db.Integer, nullable=False)
    min_interest_rate = db.Column(db.Float, nullable=False)
    max_interest_rate = db.Column(db.Float, nullable=False)
    term_months = db.Column(db.String(50))

    # Compliance / disclosure text
    compliance_note = db.Column(db.Text)
    product_disclaimer = db.Column(db.Text)

    # Appointments relationship
    appointments = db.relationship("Appointment", backref="product", lazy=True)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("loan_product.id"), nullable=False)

    contact_name = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time = db.Column(db.Time, nullable=False)

    message = db.Column(db.Text)
    email_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
