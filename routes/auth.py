from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company_name = request.form.get("company_name", "").strip()
        br_number = request.form.get("br_number", "").strip()
        established_year_str = request.form.get("established_year", "").strip()

        if not all([email, password, company_name, br_number, established_year_str]):
            flash("Please complete all required fields.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "warning")
            return render_template("auth/register.html")

        try:
            established_year = int(established_year_str)
        except ValueError:
            flash("Established year must be a valid year.", "danger")
            return render_template("auth/register.html")

        current_year = date.today().year
        if established_year < 1900 or established_year > current_year:
            flash("Established year is out of valid range.", "danger")
            return render_template("auth/register.html")

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            company_name=company_name,
            br_number=br_number,
            established_year=established_year,
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have logged out.", "info")
    return redirect(url_for("auth.login"))
