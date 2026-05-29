"""
Capstone AI Lab — Adult tier sales page + Stripe Checkout.

Self-contained blueprint. Does NOT use the existing DB Product model
(intentional — keeps AI Apps Lab cleanly separated from the CRM-style
product store in blueprints/products.py).

Routes:
    GET  /lab                  → long-form VSL sales page
    POST /lab/checkout/<tier>  → create Stripe Checkout session, redirect to Stripe
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

    if not stripe_key:
        # No live Stripe key configured — go to a graceful fallback so launch
        # doesn't blow up when the env var isn't set yet (e.g. first deploy).
        return render_template(
            "lab/checkout_pending.html",
            tier=spec,
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

    except Exception as e:
        current_app.logger.exception("Stripe checkout failed for tier=%s", tier)
        return jsonify({"error": f"Checkout error: {e}"}), 500


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
