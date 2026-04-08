from datetime import date

from flask import Flask, redirect, request, url_for
from flask_login import LoginManager, current_user

import config
from models import LoanProduct, User, db
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
        init_loan_products()

    return app


def init_loan_products():
    if LoanProduct.query.count() == 0:
        products = [
            LoanProduct(
                name="SME Flexi Loan",
                bank_name="HSBC",
                min_credit_score=80,
                max_amount=5000000,
                min_interest_rate=5.5,
                max_interest_rate=8.5,
                term_months="12,24,36,48,60",
            ),
            LoanProduct(
                name="SME Support Loan",
                bank_name="BOCHK",
                min_credit_score=60,
                max_amount=3000000,
                min_interest_rate=6.5,
                max_interest_rate=10.0,
                term_months="12,24,36,48",
            ),
            LoanProduct(
                name="SME Instalment Loan",
                bank_name="ZA Bank",
                min_credit_score=40,
                max_amount=1000000,
                min_interest_rate=8.0,
                max_interest_rate=15.0,
                term_months="6,12,24,36",
            ),
        ]
        db.session.add_all(products)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
