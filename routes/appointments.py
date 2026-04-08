from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Appointment, LoanProduct, User, db
from utils.email_draft import generate_email_draft

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointment")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@appointments_bp.route("/create", methods=["POST"])
@login_required
def create_appointment():
    product_id = request.form.get("product_id", "").strip()
    contact_name = request.form.get("contact_name", "").strip()
    contact_phone = request.form.get("contact_phone", "").strip()
    preferred_date_str = request.form.get("preferred_date", "").strip()
    preferred_time_str = request.form.get("preferred_time", "").strip()
    message = request.form.get("message", "").strip()

    if not all([product_id, contact_name, contact_phone, preferred_date_str, preferred_time_str]):
        flash("Please complete all required appointment fields.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    product = LoanProduct.query.get(product_id)
    if not product:
        flash("Selected loan product does not exist.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    try:
        preferred_date = datetime.strptime(preferred_date_str, "%Y/%m/%d").date()
        preferred_time = datetime.strptime(preferred_time_str, "%H:%M").time()
    except ValueError:
        flash("Invalid date or time format. Please use yyyy/mm/dd and HH:MM.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if preferred_date < date.today():
        flash("Preferred date cannot be earlier than today.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    appointment = Appointment(
        user_id=current_user.id,
        product_id=product.id,
        contact_name=contact_name,
        contact_phone=contact_phone,
        preferred_date=preferred_date,
        preferred_time=preferred_time,
        message=message,
    )
    db.session.add(appointment)
    db.session.flush()

    user = User.query.get(current_user.id)
    appointment.email_content = generate_email_draft(appointment, user, product)
    db.session.commit()

    return redirect(url_for("appointments.appointment_success", appointment_id=appointment.id))


@appointments_bp.route("/success/<int:appointment_id>", methods=["GET"])
@login_required
def appointment_success(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.user_id != current_user.id:
        abort(403)
    return render_template("appointments/success.html", appointment=appointment)


@appointments_bp.route("/my", methods=["GET"])
@login_required
def my_appointments():
    appointments = (
        Appointment.query.filter_by(user_id=current_user.id)
        .order_by(Appointment.created_at.desc())
        .all()
    )
    return render_template("appointments/my_appointments.html", appointments=appointments)


@appointments_bp.route("/view/<int:appointment_id>", methods=["GET"])
@login_required
def view_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.user_id != current_user.id:
        abort(403)
    return render_template("appointments/success.html", appointment=appointment)


@admin_bp.route("/appointments", methods=["GET"])
@login_required
def admin_appointments():
    if not current_user.is_admin:
        abort(403)

    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return render_template("admin/appointments.html", appointments=appointments)
