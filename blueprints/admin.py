from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from extensions import db
from auth import login_required, check_credentials
from models import Contact, Deal, Note, ActivityLog, Purchase
from sqlalchemy import func

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if check_credentials(username, password):
            session["logged_in"] = True
            session.permanent = True
            next_url = request.args.get("next", url_for("admin.dashboard"))
            return redirect(next_url)
        else:
            flash("Invalid credentials. Please try again.", "danger")

    from flask import current_app
    default_creds = (
        current_app.config["ADMIN_USER"] in ("admin", "instructor")
        and current_app.config["ADMIN_PASS"] in ("admin", "changeme", "SaturdayWorkshop2026!")
    )
    return render_template("admin/login.html", default_creds=default_creds)


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "total_contacts": Contact.query.count(),
        "total_leads": Contact.query.filter(Contact.status == "Lead").count(),
        "pipeline_value": float(db.session.query(func.coalesce(func.sum(Deal.value), 0)).filter(
            Deal.stage.notin_(["Won", "Lost"])
        ).scalar()),
        "total_revenue": float(db.session.query(func.coalesce(func.sum(Deal.value), 0)).filter(
            Deal.stage == "Won"
        ).scalar()),
        "total_deals": Deal.query.count(),
        "won_deals": Deal.query.filter(Deal.stage == "Won").count(),
    }
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    from models import ContentItem
    content_total = ContentItem.query.count()
    content_ready = ContentItem.query.filter_by(status="ReadyToPost").count()
    content_published = ContentItem.query.filter_by(status="published").count()

    # Check setup completion for welcome banner
    import os
    setup_done = bool(
        os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_activity=recent_activity,
        content_total=content_total,
        content_ready=content_ready,
        content_published=content_published,
        setup_done=setup_done,
    )


@admin_bp.route("/contacts")
@login_required
def contacts():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Contact.query
    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Contact.name.ilike(search),
                Contact.email.ilike(search),
                Contact.company.ilike(search),
            )
        )
    if status_filter:
        query = query.filter(Contact.status == status_filter)

    contacts_list = query.order_by(Contact.created_at.desc()).all()
    return render_template("admin/contacts.html", contacts=contacts_list, q=q, status_filter=status_filter)


@admin_bp.route("/contacts/<int:contact_id>")
@login_required
def contact_detail(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    activities = ActivityLog.query.filter_by(contact_id=contact_id).order_by(ActivityLog.created_at.desc()).limit(20).all()
    all_deals = Deal.query.filter_by(contact_id=contact_id).all()

    return render_template("admin/contact_detail.html", contact=contact, activities=activities, deals=all_deals)


@admin_bp.route("/settings")
@login_required
def settings():
    from models import Setting
    import os
    # Load DB settings + env vars (env vars take priority for display)
    settings = {}
    for s in Setting.query.all():
        settings[s.key] = s.value
    # Also check env vars for API keys so indicators work on first run
    env_keys = [
        "OPENAI_API_KEY", "OPENROUTER_API_KEY", "CHAT_PROVIDER",
        "FIRECRAWL_API_KEY", "KIE_AI_API_KEY", "GETLATE_API_KEY",
        "ZERNIO_API_KEY", "ZERNIO_PROFILE_ID",
        "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY",
        "RESEND_API_KEY", "RESEND_FROM_EMAIL",
        "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME", "R2_PUBLIC_URL",
    ]
    for key in env_keys:
        if key not in settings or not settings[key]:
            env_val = os.environ.get(key, "")
            if env_val:
                settings[key] = env_val
    return render_template("admin/settings.html", settings=settings)


@admin_bp.route("/settings", methods=["POST"])
@login_required
def save_settings():
    from models import Setting
    import os
    # List of setting keys to save
    keys = [
        "BUSINESS_NAME", "OPENAI_API_KEY", "CHAT_PROVIDER",
        "OPENROUTER_API_KEY", "FIRECRAWL_API_KEY",
        "KIE_AI_API_KEY", "GETLATE_API_KEY",
        "ZERNIO_API_KEY", "ZERNIO_PROFILE_ID",
        "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY",
        "RESEND_API_KEY", "RESEND_FROM_EMAIL",
        "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME", "R2_PUBLIC_URL",
    ]
    for key in keys:
        value = request.form.get(key, "").strip()
        if value:  # Only save non-empty values
            Setting.set(key, value)
            os.environ[key] = value  # Immediate pickup by services
    flash("Settings saved successfully!", "success")
    return redirect(url_for("admin.settings"))


@admin_bp.route("/deals")
@login_required
def deals():
    stages = ["New Lead", "Contacted", "Proposal", "Negotiation", "Won", "Lost"]
    stage_filter = request.args.get("stage", "")
    search = request.args.get("q", "").strip()

    query = Deal.query
    if stage_filter:
        query = query.filter_by(stage=stage_filter)
    if search:
        query = query.filter(Deal.title.ilike(f"%{search}%"))

    all_deals = query.order_by(Deal.created_at.desc()).all()
    all_contacts = Contact.query.order_by(Contact.name).all()

    # Stage summary for filter badges
    stage_counts = {}
    for stage in stages:
        stage_counts[stage] = Deal.query.filter_by(stage=stage).count()

    pipeline_total = sum(float(d.value or 0) for d in Deal.query.filter(Deal.stage.notin_(["Won", "Lost"])).all())

    return render_template("admin/deals.html",
        deals=all_deals, stages=stages, contacts=all_contacts,
        stage_filter=stage_filter, search=search,
        stage_counts=stage_counts, pipeline_total=pipeline_total)


@admin_bp.route("/pages")
@login_required
def pages():
    """Website pages management — show/hide pages, funnel grouping."""
    website_pages = [
        {"name": "Landing Page", "path": "/lp", "active": True, "type": "funnel"},
        {"name": "Sales Page", "path": "/sales", "active": True, "type": "funnel"},
        {"name": "Thank You", "path": "/lp/thank-you", "active": True, "type": "funnel"},
        {"name": "Store", "path": "/products/store", "active": True, "type": "standalone"},
        {"name": "Public Booking", "path": "/bookings/book", "active": True, "type": "standalone"},
        {"name": "Onboarding Survey", "path": "/onboarding/", "active": True, "type": "standalone"},
    ]
    return render_template("admin/pages.html", pages=website_pages)


@admin_bp.route("/analytics")
@login_required
def analytics():
    """Umami-style analytics dashboard with demo data."""
    from models import PageView, Contact
    from datetime import datetime, timedelta
    import random

    # Generate demo analytics data
    now = datetime.utcnow()
    hours_data = []
    for i in range(24):
        h = now - timedelta(hours=23 - i)
        visitors = random.randint(5, 80)
        views = visitors + random.randint(10, 120)
        hours_data.append({
            "hour": h.strftime("%I %p"),
            "visitors": visitors,
            "views": views,
        })

    total_views = sum(h["views"] for h in hours_data)
    total_visitors = sum(h["visitors"] for h in hours_data)
    total_visits = int(total_visitors * 1.3)
    bounce_rate = random.randint(35, 65)
    avg_duration = f"{random.randint(1, 4)}m {random.randint(0, 59)}s"

    # Top pages
    top_pages = [
        {"page": "/", "views": random.randint(200, 500), "pct": 0},
        {"page": "/lp", "views": random.randint(100, 300), "pct": 0},
        {"page": "/sales", "views": random.randint(50, 200), "pct": 0},
        {"page": "/products/store", "views": random.randint(30, 150), "pct": 0},
        {"page": "/onboarding/", "views": random.randint(20, 100), "pct": 0},
        {"page": "/bookings/book", "views": random.randint(10, 80), "pct": 0},
    ]
    tp_total = sum(p["views"] for p in top_pages)
    for p in top_pages:
        p["pct"] = round(p["views"] / tp_total * 100) if tp_total else 0

    # Top referrers
    referrers = [
        {"source": "google.com", "views": random.randint(50, 200)},
        {"source": "facebook.com", "views": random.randint(30, 150)},
        {"source": "instagram.com", "views": random.randint(20, 100)},
        {"source": "direct", "views": random.randint(40, 180)},
        {"source": "tiktok.com", "views": random.randint(10, 60)},
    ]
    ref_total = sum(r["views"] for r in referrers)
    for r in referrers:
        r["pct"] = round(r["views"] / ref_total * 100) if ref_total else 0

    return render_template("admin/analytics.html",
        hours_data=hours_data, total_views=total_views,
        total_visitors=total_visitors, total_visits=total_visits,
        bounce_rate=bounce_rate, avg_duration=avg_duration,
        top_pages=top_pages, referrers=referrers)
