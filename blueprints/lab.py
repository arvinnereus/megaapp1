"""
Capstone AI Lab — Adult tier sales page + Stripe Checkout.

Self-contained blueprint. Does NOT use the existing DB Product model
(intentional — keeps AI Apps Lab cleanly separated from the CRM-style
product store in blueprints/products.py).

Routes:
    GET  /lab                  → long-form VSL sales page
    POST /lab/checkout/<tier>  → create Stripe Checkout session, redirect to Stripe
    POST /lab/reserve          → "reserve your seat" form (when checkout isn't live yet)
    GET  /lab/success          → thank-you page (parsed from Stripe session_id query param)
    GET  /lab/cancel           → cancel page

Tiers (USD):
    lite    $97
    pro     $497
    master  $1997
    bump    $47   (order bump on Lite checkout — adds "100 Production-Tested AI Prompts")
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, abort

lab_bp = Blueprint("lab", __name__)


def _is_valid_stripe_key(key: str) -> bool:
    """Sanity-check key format BEFORE handing it to Stripe.

    Catches the common 'wrong env var pasted' mistake — e.g. someone
    accidentally pastes the Flask SECRET_KEY into STRIPE_SECRET_KEY.
    """
    return bool(key) and (key.startswith("sk_test_") or key.startswith("sk_live_"))


TIERS = {
    "lite": {
        "name": "AI Apps Lab — Lite",
        "price_usd": 97,
        "description": "12 weeks of recorded content + templates + 60-day ship-it guarantee",
    },
    "pro": {
        "name": "AI Apps Lab — Pro",
        "price_usd": 497,
        "description": "Lite + community + monthly Q&A archive + AI project review",
    },
    "master": {
        "name": "AI Apps Lab — Mastermind",
        "price_usd": 1997,
        "description": "Pro + 4 live group strategy calls/yr + 90-day inbox access",
    },
}

ORDER_BUMP = {
    "name": "100 Production-Tested AI Prompts",
    "price_usd": 47,
}


# --- SALES PAGE ---

@lab_bp.route("/", methods=["GET"], strict_slashes=False)
def sales_page():
    """Long-form VSL — the public sales page for Adult tier."""
    return render_template(
        "lab/sales_page.html",
        tiers=TIERS,
        bump=ORDER_BUMP,
    )


# --- CHECKOUT ---

@lab_bp.route("/checkout/<tier>", methods=["POST", "GET"], strict_slashes=False)
def checkout(tier):
    """Create a Stripe Checkout Session for the chosen tier.

    GET also accepted (so CTA buttons can link directly without a JS form).
    Returns a 303 redirect to Stripe-hosted checkout, OR JSON if Accept: application/json.
    """
    tier = tier.lower().strip()
    if tier not in TIERS:
        abort(404)

    spec = TIERS[tier]
    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")

    # Optional order bump (only offered on Lite checkout — see template)
    add_bump = request.values.get("bump", "").lower() in ("1", "true", "yes", "on")

    # Validate key format BEFORE calling Stripe — catches the common
    # "wrong env var pasted" mistake and the "key not set yet" case in one step.
    if not _is_valid_stripe_key(stripe_key):
        current_app.logger.warning(
            "Stripe key missing or malformed for tier=%s — showing reservation page", tier
        )
        return render_template(
            "lab/checkout_pending.html",
            tier=spec,
            tier_slug=tier,
            bump=ORDER_BUMP if add_bump else None,
        ), 200

    try:
        import stripe
        stripe.api_key = stripe_key

        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": spec["name"], "description": spec["description"]},
                "unit_amount": spec["price_usd"] * 100,
            },
            "quantity": 1,
        }]
        if add_bump:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": ORDER_BUMP["name"]},
                    "unit_amount": ORDER_BUMP["price_usd"] * 100,
                },
                "quantity": 1,
            })

        session_obj = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=url_for("lab.success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("lab.cancel", _external=True),
            metadata={
                "product": "capstone_ai_lab_adult",
                "tier": tier,
                "bump": "1" if add_bump else "0",
            },
            allow_promotion_codes=True,
        )

        if request.accept_mimetypes.best == "application/json":
            return jsonify({"checkout_url": session_obj.url, "session_id": session_obj.id})
        return redirect(session_obj.url, code=303)

    except stripe.error.AuthenticationError:
        # Key was the right format but Stripe rejected it (revoked, wrong env, typo).
        # Gracefully fall back to reservation page instead of a JSON error.
        current_app.logger.warning("Stripe authentication failed — falling back to reservation page")
        return render_template(
            "lab/checkout_pending.html",
            tier=spec,
            tier_slug=tier,
            bump=ORDER_BUMP if add_bump else None,
        ), 200
    except Exception:
        # Catch-all: render the same reservation page so the buyer NEVER sees
        # a raw JSON error. Logs capture the real exception for debugging.
        current_app.logger.exception("Stripe checkout failed for tier=%s", tier)
        return render_template(
            "lab/checkout_pending.html",
            tier=spec,
            tier_slug=tier,
            bump=ORDER_BUMP if add_bump else None,
        ), 200


# --- RESERVATION (collects interest while real checkout isn't live) ---

@lab_bp.route("/reserve", methods=["POST"], strict_slashes=False)
def reserve():
    """Capture interest when checkout isn't fully wired yet.

    Records the contact in DB + notifies Arvin via Resend + confirms to buyer.
    Resend failures are logged but never block the user-facing flow.
    """
    from extensions import db
    from models import Contact, log_activity

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    tier = (request.form.get("tier") or "unknown").strip()

    if not email or "@" not in email:
        return render_template(
            "lab/reserved.html",
            ok=False,
            message="That email doesn't look right — give it another try?",
            tier=tier,
        ), 400

    # Find or create contact (idempotent — re-submits update the existing record)
    contact = Contact.query.filter_by(email=email).first()
    if not contact:
        contact = Contact(
            name=name or email.split("@")[0],
            email=email,
            status="Reservation",
            lead_source=f"AI Apps Lab — reserved {tier}",
        )
        db.session.add(contact)
        db.session.flush()
        log_activity(
            "contact_created",
            f"AI Apps Lab reservation: {contact.name} ({tier})",
            contact_id=contact.id,
        )
    else:
        # Existing contact reserving — bump notes
        log_activity(
            "reservation_repeat",
            f"Repeat reservation from {contact.name} ({tier})",
            contact_id=contact.id,
        )

    db.session.commit()

    # Resend emails (best-effort — never block the flow on failure)
    _send_reservation_emails(name or contact.name, email, tier)

    return render_template("lab/reserved.html", ok=True, tier=tier, name=name or contact.name)


def _send_reservation_emails(name: str, email: str, tier: str) -> None:
    """Send buyer confirmation + Arvin notification via Resend. Best-effort."""
    import requests
    resend_key = current_app.config.get("RESEND_API_KEY", "")
    from_email = current_app.config.get("RESEND_FROM_EMAIL", "") or "arvin@capstoneailab.com"

    if not resend_key:
        current_app.logger.info("Resend not configured — skipping reservation emails")
        return

    headers = {"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"}

    # Buyer confirmation
    buyer_html = f"""
    <p>Hi {name},</p>
    <p>Thanks for reserving your seat in <strong>Capstone AI Lab — {tier.title()}</strong>.</p>
    <p>Quick context: I'm finalising the live checkout this week. You'll be the first
    to get the link — usually within 24-48 hours of reserving.</p>
    <p>If you have a specific question about the program, just hit reply. I read everything.</p>
    <p>Warmly,<br>Arvin Yeo<br>Capstone AI Lab</p>
    """
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers=headers,
            json={
                "from": from_email,
                "to": [email],
                "subject": f"You're reserved — Capstone AI Lab {tier.title()}",
                "html": buyer_html,
            },
            timeout=10,
        )
    except Exception:
        current_app.logger.warning("Buyer confirmation email failed for %s", email)

    # Arvin notification
    arvin_html = f"""
    <p>New AI Apps Lab reservation:</p>
    <ul>
      <li><strong>Name:</strong> {name}</li>
      <li><strong>Email:</strong> {email}</li>
      <li><strong>Tier:</strong> {tier}</li>
    </ul>
    <p>Reach out within 48 hours with a personal link.</p>
    """
    try:
        requests.post(
            "https://api.resend.com/emails",
            headers=headers,
            json={
                "from": from_email,
                "to": ["arvin@capstoneailab.com"],
                "subject": f"New Lab reservation: {name} ({tier})",
                "html": arvin_html,
            },
            timeout=10,
        )
    except Exception:
        current_app.logger.warning("Arvin notification email failed")


# --- SUCCESS / CANCEL ---

@lab_bp.route("/success", methods=["GET"], strict_slashes=False)
def success():
    """Stripe redirects here after successful payment.

    NOTE: source of truth for fulfilment is the webhook handler in
    blueprints/stripe_webhook.py — this page is just a thank-you screen.
    Buyers MAY close the tab before redirect, so never trust the redirect alone.
    """
    session_id = request.args.get("session_id", "")
    return render_template("lab/checkout_success.html", session_id=session_id)


@lab_bp.route("/cancel", methods=["GET"], strict_slashes=False)
def cancel():
    return render_template("lab/checkout_cancel.html")
