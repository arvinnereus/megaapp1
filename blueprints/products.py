from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from extensions import db
from models import Product, Purchase, Contact, log_activity
from auth import login_required

products_bp = Blueprint("products", __name__)


# --- ADMIN PAGES ---

@products_bp.route("/admin/products")
@login_required
def products_list():
    status_filter = request.args.get("status", "").strip()

    query = Product.query
    if status_filter == "active":
        query = query.filter(Product.active == True)
    elif status_filter == "inactive":
        query = query.filter(Product.active == False)

    products = query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=products, status_filter=status_filter)


@products_bp.route("/admin/products/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    purchases = Purchase.query.filter_by(product_id=product_id).order_by(Purchase.purchased_at.desc()).all()
    stripe_configured = bool(current_app.config.get("STRIPE_SECRET_KEY"))
    return render_template("admin/product_detail.html", product=product, purchases=purchases, stripe_configured=stripe_configured)


# --- API ROUTES ---

@products_bp.route("/api/products", methods=["POST"])
@login_required
def create_product():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    product = Product(
        name=data["name"],
        description=data.get("description"),
        price=data.get("price", 0),
        product_type=data.get("product_type", "paid"),
        delivery_url=data.get("delivery_url"),
        stripe_price_id=data.get("stripe_price_id"),
        image_url=data.get("image_url"),
        active=data.get("active", True),
    )
    db.session.add(product)
    db.session.flush()
    log_activity("product_created", f"Created product: {product.name}")
    db.session.commit()
    return jsonify(product.to_dict()), 201


@products_bp.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    for field in ["name", "description", "price", "product_type", "delivery_url", "stripe_price_id", "image_url"]:
        if field in data:
            setattr(product, field, data[field])

    if "active" in data:
        product.active = bool(data["active"])

    log_activity("product_updated", f"Updated product: {product.name}")
    db.session.commit()
    return jsonify(product.to_dict())


@products_bp.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    db.session.delete(product)
    log_activity("product_deleted", f"Deleted product: {name}")
    db.session.commit()
    return jsonify({"message": f"Product '{name}' deleted"})


# --- PUBLIC STORE ---

@products_bp.route("/store")
def store():
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    return render_template("public/store.html", products=products)


# --- CHECKOUT ---

@products_bp.route("/api/checkout/<int:product_id>", methods=["POST"])
def create_checkout(product_id):
    product = Product.query.get_or_404(product_id)

    if not product.active:
        return jsonify({"error": "This product is not available"}), 400

    # Collect buyer info from JSON body
    data = request.get_json() or {}
    buyer_email = data.get("email", "").strip()
    buyer_name = data.get("name", "").strip()

    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")

    if stripe_key:
        # Live Stripe mode
        try:
            import stripe
            stripe.api_key = stripe_key

            checkout_params = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": product.stripe_price_id,
                    "quantity": 1,
                }] if product.stripe_price_id else [{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": product.name},
                        "unit_amount": int(float(product.price) * 100),
                    },
                    "quantity": 1,
                }],
                "mode": "payment",
                "success_url": url_for("products.checkout_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": url_for("products.checkout_cancel", _external=True),
            }

            if buyer_email:
                checkout_params["customer_email"] = buyer_email

            session = stripe.checkout.Session.create(**checkout_params)
            return jsonify({"checkout_url": session.url, "session_id": session.id})
        except Exception as e:
            return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    else:
        # Mock mode — simulate checkout
        import uuid
        mock_session_id = f"mock_{uuid.uuid4().hex[:16]}"

        # Find or create contact for the buyer
        contact = None
        if buyer_email:
            contact = Contact.query.filter_by(email=buyer_email).first()
            if not contact:
                contact = Contact(
                    name=buyer_name or buyer_email.split("@")[0],
                    email=buyer_email,
                    status="Customer",
                    lead_source="Store Purchase",
                )
                db.session.add(contact)
                db.session.flush()
                log_activity("contact_created", f"New customer from store: {contact.name}", contact_id=contact.id)

        # Create purchase record
        purchase = Purchase(
            contact_id=contact.id if contact else None,
            product_id=product.id,
            stripe_session_id=mock_session_id,
            amount=product.price if product.product_type == "paid" else 0,
            status="completed",
        )
        db.session.add(purchase)
        log_activity("purchase_completed", f"Mock purchase: {product.name}" + (f" by {contact.name}" if contact else ""))
        db.session.commit()

        # Trigger email
        try:
            from blueprints.email import send_trigger_email
            send_trigger_email("purchase_confirmation", contact, product)
        except Exception:
            pass

        success_url = url_for("products.checkout_success", _external=True) + f"?session_id={mock_session_id}"
        return jsonify({"checkout_url": success_url, "session_id": mock_session_id, "mock": True})


@products_bp.route("/checkout/success")
def checkout_success():
    session_id = request.args.get("session_id", "")

    stripe_key = current_app.config.get("STRIPE_SECRET_KEY", "")

    if stripe_key and session_id and not session_id.startswith("mock_"):
        # Live Stripe — retrieve session and create purchase record
        try:
            import stripe
            stripe.api_key = stripe_key
            checkout_session = stripe.checkout.Session.retrieve(session_id)

            # Check if purchase already recorded
            existing = Purchase.query.filter_by(stripe_session_id=session_id).first()
            if not existing:
                # Find or create contact
                customer_email = checkout_session.get("customer_details", {}).get("email", "")
                contact = None
                if customer_email:
                    contact = Contact.query.filter_by(email=customer_email).first()
                    if not contact:
                        customer_name = checkout_session.get("customer_details", {}).get("name", customer_email.split("@")[0])
                        contact = Contact(
                            name=customer_name,
                            email=customer_email,
                            status="Customer",
                            lead_source="Store Purchase",
                        )
                        db.session.add(contact)
                        db.session.flush()
                        log_activity("contact_created", f"New customer from store: {contact.name}", contact_id=contact.id)

                # Determine product from metadata or line items
                product = None
                line_items = stripe.checkout.Session.list_line_items(session_id)
                if line_items and line_items.data:
                    amount = line_items.data[0].amount_total / 100
                else:
                    amount = checkout_session.amount_total / 100 if checkout_session.amount_total else 0

                purchase = Purchase(
                    contact_id=contact.id if contact else None,
                    product_id=None,
                    stripe_session_id=session_id,
                    amount=amount,
                    status="completed",
                )
                db.session.add(purchase)
                log_activity("purchase_completed", f"Stripe purchase completed" + (f" by {contact.name}" if contact else ""))
                db.session.commit()

                # Trigger email
                try:
                    from blueprints.email import send_trigger_email
                    send_trigger_email("purchase_confirmation", contact, product)
                except Exception:
                    pass
        except Exception:
            pass

    return render_template("public/checkout_success.html", session_id=session_id)


@products_bp.route("/checkout/cancel")
def checkout_cancel():
    return render_template("public/checkout_cancel.html")
