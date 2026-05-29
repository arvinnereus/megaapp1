"""
Stripe webhook handler — source of truth for AI Apps Lab purchase fulfilment.

On `checkout.session.completed`:
  1. Find or create a Contact for the buyer
  2. Create a Purchase record (DB)
  3. Trigger welcome email via Resend (using existing send_trigger_email helper)
  4. (Future) enrol the buyer in Skool / Memberstack via their APIs

Stripe sends events with a signature header that we verify using
STRIPE_WEBHOOK_SECRET. Never trust unsigned bodies.

Local testing:
    stripe listen --forward-to localhost:8000/webhook/stripe
"""
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models import Contact, Purchase, log_activity

stripe_webhook_bp = Blueprint("stripe_webhook", __name__)


@stripe_webhook_bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")

    if not webhook_secret or not stripe_key:
        # Reject loudly so misconfiguration is visible in Render logs
        return jsonify({"error": "webhook not configured"}), 503

    try:
        import stripe
        stripe.api_key = stripe_key
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({"error": "invalid payload"}), 400
    except Exception as e:
        # Includes stripe.error.SignatureVerificationError
        current_app.logger.warning("Stripe webhook signature verification failed: %s", e)
        return jsonify({"error": "invalid signature"}), 400

    if event["type"] == "checkout.session.completed":
        try:
            _handle_checkout_completed(event["data"]["object"])
        except Exception:
            current_app.logger.exception("Failed to fulfil checkout session")
            # Returning 500 makes Stripe retry — desirable for transient failures
            return jsonify({"error": "fulfilment failed"}), 500

    # Acknowledge all other events so Stripe doesn't retry forever
    return jsonify({"received": True}), 200


def _handle_checkout_completed(session_obj: dict) -> None:
    session_id = session_obj.get("id", "")
    customer_details = session_obj.get("customer_details") or {}
    customer_email = (customer_details.get("email") or "").strip()
    customer_name = (customer_details.get("name") or "").strip()
    amount_total = (session_obj.get("amount_total") or 0) / 100
    metadata = session_obj.get("metadata") or {}
    tier = metadata.get("tier", "")
    product_slug = metadata.get("product", "")

    # Idempotency — don't double-record if Stripe retries
    existing = Purchase.query.filter_by(stripe_session_id=session_id).first()
    if existing:
        return

    # Find or create contact
    contact = None
    if customer_email:
        contact = Contact.query.filter_by(email=customer_email).first()
        if not contact:
            contact = Contact(
                name=customer_name or customer_email.split("@")[0],
                email=customer_email,
                status="Customer",
                lead_source=f"AI Apps Lab — {tier or 'unknown'}",
            )
            db.session.add(contact)
            db.session.flush()
            log_activity(
                "contact_created",
                f"AI Apps Lab buyer: {contact.name}",
                contact_id=contact.id,
            )

    purchase = Purchase(
        contact_id=contact.id if contact else None,
        product_id=None,  # AI Apps Lab tiers aren't in the DB Product table by design
        stripe_session_id=session_id,
        amount=amount_total,
        status="completed",
    )
    db.session.add(purchase)
    log_activity(
        "purchase_completed",
        f"AI Apps Lab {tier} ({product_slug}) — ${amount_total:.2f}"
        + (f" by {contact.name}" if contact else ""),
    )
    db.session.commit()

    # Welcome email — uses existing EmailTemplate with trigger_type='purchase_confirmation'
    # if one exists; silently skips otherwise. The lead-magnet drips run from Resend
    # broadcasts/automations, not from this webhook.
    if contact:
        try:
            from blueprints.email import send_trigger_email
            send_trigger_email("purchase_confirmation", contact, None)
        except Exception:
            current_app.logger.warning("Welcome email failed for %s", customer_email)
