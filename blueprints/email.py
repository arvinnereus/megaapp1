from flask import Blueprint, render_template, request, jsonify, current_app
from extensions import db
from models import EmailTemplate, EmailLog
from auth import login_required

email_bp = Blueprint("email", __name__)


# --- HELPER ---

def send_trigger_email(trigger_type, contact, product=None):
    """Send an email based on trigger type. Uses Resend if API key set, otherwise logs as mock."""
    from flask import current_app
    from models import EmailTemplate, EmailLog

    template = EmailTemplate.query.filter_by(trigger_type=trigger_type, active=True).first()
    if not template:
        return None

    # Build subject and body with variable substitution
    subject = template.subject.replace("{{name}}", contact.name or "")
    body = template.body_html.replace("{{name}}", contact.name or "")
    if product:
        body = body.replace("{{product_name}}", product.name or "")
        body = body.replace("{{delivery_url}}", product.delivery_url or "#")
        body = body.replace("{{price}}", f"${float(product.price):,.2f}" if product.price else "$0")

    # Replace lead magnet URL
    lead_magnet_url = current_app.config.get("LEAD_MAGNET_URL", "#")
    body = body.replace("{{lead_magnet_url}}", lead_magnet_url)

    resend_key = current_app.config.get("RESEND_API_KEY", "")
    from_email = current_app.config.get("RESEND_FROM_EMAIL", "hello@yourdomain.com")
    status = "mock"

    if resend_key and contact.email:
        import requests
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [contact.email], "subject": subject, "html": body},
                timeout=10,
            )
            status = "sent" if resp.ok else "failed"
        except Exception:
            status = "failed"

    # Log the email
    log = EmailLog(
        template_id=template.id,
        contact_id=contact.id,
        to_email=contact.email or "",
        subject=subject,
        status=status,
    )
    db.session.add(log)
    db.session.commit()
    return log


# --- ADMIN PAGES ---

@email_bp.route("/admin/email-templates")
@login_required
def templates_list():
    templates = EmailTemplate.query.order_by(EmailTemplate.created_at.desc()).all()
    resend_configured = bool(current_app.config.get("RESEND_API_KEY"))
    return render_template("admin/email_templates.html", templates=templates, resend_configured=resend_configured)


@email_bp.route("/admin/email-log")
@login_required
def email_log():
    logs = EmailLog.query.order_by(EmailLog.sent_at.desc()).all()
    return render_template("admin/email_log.html", logs=logs)


# --- API ROUTES ---

@email_bp.route("/api/email-templates/<int:template_id>", methods=["PUT"])
@login_required
def update_template(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    data = request.get_json()

    if "subject" in data:
        template.subject = data["subject"]
    if "body_html" in data:
        template.body_html = data["body_html"]
    if "active" in data:
        template.active = bool(data["active"])

    db.session.commit()
    return jsonify(template.to_dict())
