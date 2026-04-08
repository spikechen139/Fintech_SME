def generate_email_draft(appointment, user, product):
    message = appointment.message.strip() if appointment.message else "N/A"
    return f"""
<p><strong>Subject:</strong> Loan Product Appointment Request - {user.company_name}</p>
<p>Dear {product.bank_name} Loan Manager,</p>
<p>
Our company {user.company_name} (BR No.: {user.br_number}) is interested in your
"{product.name}" product and would like to request an appointment.
</p>
<p>
Proposed appointment time: {appointment.preferred_date.strftime("%Y-%m-%d")} at
{appointment.preferred_time.strftime("%H:%M")}
</p>
<p>Contact person: {appointment.contact_name}<br>
Phone: {appointment.contact_phone}<br>
Message: {message}</p>
<p>
Please let us know if this time works for you or suggest an alternative.
</p>
<p>Best regards,<br>{user.company_name}</p>
""".strip()
