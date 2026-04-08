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
    credit_score = db.Column(db.Integer, default=0)
    credit_analysis = db.Column(db.Text, default="")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    financial_data = db.relationship("FinancialData", backref="user", uselist=False)
    appointments = db.relationship("Appointment", backref="user", lazy=True)


class FinancialData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    annual_revenue = db.Column(db.Integer)
    net_profit = db.Column(db.Integer)
    has_bank_debt = db.Column(db.Boolean)
    has_collateral = db.Column(db.Boolean)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoanProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    min_credit_score = db.Column(db.Integer, nullable=False)
    max_amount = db.Column(db.Integer, nullable=False)
    min_interest_rate = db.Column(db.Float, nullable=False)
    max_interest_rate = db.Column(db.Float, nullable=False)
    term_months = db.Column(db.String(50))


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

    product = db.relationship("LoanProduct", backref="appointments")
