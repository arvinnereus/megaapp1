from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Contact, log_activity

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return redirect(url_for("public.landing"))


@public_bp.route("/lp")
def landing():
    return render_template("public/landing.html")


@public_bp.route("/lp/submit", methods=["POST"])
def landing_submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        flash("Please provide your name and email.", "danger")
        return redirect(url_for("public.landing"))

    # Check if contact already exists
    existing = Contact.query.filter_by(email=email).first()
    if not existing:
        contact = Contact(
            name=name,
            email=email,
            status="Lead",
            lead_source="Website Form",
        )
        db.session.add(contact)
        log_activity("contact_created", f"New lead from landing page: {name}", contact_id=None)
        db.session.commit()
        # Update activity with actual contact_id
        from models import ActivityLog
        last = ActivityLog.query.order_by(ActivityLog.id.desc()).first()
        if last:
            last.contact_id = contact.id
            db.session.commit()

    return redirect(url_for("public.thank_you"))


@public_bp.route("/lp/thank-you")
def thank_you():
    return render_template("public/thank_you.html")


@public_bp.route("/sales")
def sales():
    return render_template("public/sales.html")
