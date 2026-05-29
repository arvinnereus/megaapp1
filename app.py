import os
from flask import Flask, session
from dotenv import load_dotenv

from extensions import db

load_dotenv()


def create_app():
    app = Flask(__name__)

    # --- Database ---
    database_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    # Fix legacy postgres:// URLs (Railway still emits these)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Security ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
    app.config["ADMIN_USER"] = os.environ.get("ADMIN_USER", "admin")
    app.config["ADMIN_PASS"] = os.environ.get("ADMIN_PASS", "admin")

    # --- Branding ---
    app.config["BUSINESS_NAME"] = os.environ.get("BUSINESS_NAME", "All-in-One Business App")

    # --- Feature Toggles ---
    app.config["FEATURE_PRODUCTS"]  = os.environ.get("FEATURE_PRODUCTS",  "true").lower() == "true"
    app.config["FEATURE_CLIENTS"]   = os.environ.get("FEATURE_CLIENTS",   "true").lower() == "true"
    app.config["FEATURE_TASKS"]     = os.environ.get("FEATURE_TASKS",     "true").lower() == "true"
    app.config["FEATURE_EMAIL"]     = os.environ.get("FEATURE_EMAIL",     "true").lower() == "true"
    app.config["FEATURE_ANALYTICS"] = os.environ.get("FEATURE_ANALYTICS", "true").lower() == "true"
    app.config["FEATURE_BOOKINGS"]  = os.environ.get("FEATURE_BOOKINGS",  "true").lower() == "true"
    app.config["FEATURE_AVATAR"]    = os.environ.get("FEATURE_AVATAR",    "true").lower() == "true"

    # --- Jackie AI / OpenAI ---
    app.config["OPENAI_API_KEY"]    = os.environ.get("OPENAI_API_KEY", "")
    app.config["CHAT_PROVIDER"]     = os.environ.get("CHAT_PROVIDER", "openai")
    app.config["OPENAI_CHAT_MODEL"] = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # --- Umami Analytics ---
    app.config["UMAMI_WEBSITE_ID"]  = os.environ.get("UMAMI_WEBSITE_ID", "")
    app.config["UMAMI_SCRIPT_URL"]  = os.environ.get("UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js")

    # --- Zernio (social media publishing, formerly GetLate) ---
    app.config["ZERNIO_API_KEY"]    = os.environ.get("ZERNIO_API_KEY", os.environ.get("GETLATE_API_KEY", ""))
    app.config["ZERNIO_PROFILE_ID"] = os.environ.get("ZERNIO_PROFILE_ID", "")

    # --- CRM Integration Keys ---
    app.config["STRIPE_CHECKOUT_URL"]   = os.environ.get("STRIPE_CHECKOUT_URL", "")
    app.config["LEAD_MAGNET_URL"]       = os.environ.get("LEAD_MAGNET_URL", "")
    app.config["OPENROUTER_API_KEY"]    = os.environ.get("OPENROUTER_API_KEY", "")

    # --- Content Automation Keys ---
    app.config["FIRECRAWL_API_KEY"]     = os.environ.get("FIRECRAWL_API_KEY", "")
    app.config["KIE_AI_API_KEY"]        = os.environ.get("KIE_AI_API_KEY", "")
    app.config["GETLATE_API_KEY"]       = os.environ.get("GETLATE_API_KEY", "")

    # --- Stripe ---
    app.config["STRIPE_SECRET_KEY"]      = os.environ.get("STRIPE_SECRET_KEY", "")
    app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    app.config["STRIPE_WEBHOOK_SECRET"]  = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # --- Resend (email) ---
    app.config["RESEND_API_KEY"]    = os.environ.get("RESEND_API_KEY", "")
    app.config["RESEND_FROM_EMAIL"] = os.environ.get("RESEND_FROM_EMAIL", "")

    # --- Cloudflare R2 Storage ---
    app.config["R2_ACCOUNT_ID"]        = os.environ.get("R2_ACCOUNT_ID", "")
    app.config["R2_ACCESS_KEY_ID"]     = os.environ.get("R2_ACCESS_KEY_ID", "")
    app.config["R2_SECRET_ACCESS_KEY"] = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    app.config["R2_BUCKET_NAME"]       = os.environ.get("R2_BUCKET_NAME", "")
    app.config["R2_PUBLIC_URL"]        = os.environ.get("R2_PUBLIC_URL", "")

    # --- Init extensions ---
    db.init_app(app)

    # --- Register blueprints ---
    from blueprints.public import public_bp
    from blueprints.admin import admin_bp
    from blueprints.api import api_bp
    from blueprints.content import content_bp
    from blueprints.content_api import content_api_bp
    from blueprints.help import help_bp

    app.register_blueprint(public_bp,     url_prefix="/")
    app.register_blueprint(admin_bp,      url_prefix="/admin")
    app.register_blueprint(api_bp,        url_prefix="/api")
    app.register_blueprint(content_bp,    url_prefix="/content")
    app.register_blueprint(content_api_bp, url_prefix="/content/api")
    app.register_blueprint(help_bp,       url_prefix="/help")

    from blueprints.jackie import jackie_bp
    app.register_blueprint(jackie_bp,    url_prefix="/jackie")

    from blueprints.onboarding import onboarding_bp
    app.register_blueprint(onboarding_bp, url_prefix="/onboarding")

    if app.config["FEATURE_BOOKINGS"]:
        from blueprints.bookings import bookings_bp
        app.register_blueprint(bookings_bp, url_prefix="/bookings")

    if app.config["FEATURE_PRODUCTS"]:
        from blueprints.products import products_bp
        app.register_blueprint(products_bp, url_prefix="/products")

    if app.config["FEATURE_CLIENTS"]:
        from blueprints.clients import clients_bp
        app.register_blueprint(clients_bp, url_prefix="/clients")

    if app.config["FEATURE_TASKS"]:
        from blueprints.tasks import tasks_bp
        app.register_blueprint(tasks_bp, url_prefix="/tasks")

    if app.config["FEATURE_EMAIL"]:
        from blueprints.email import email_bp
        app.register_blueprint(email_bp, url_prefix="/email")

    if app.config["FEATURE_AVATAR"]:
        from blueprints.avatar import avatar_bp
        app.register_blueprint(avatar_bp, url_prefix="/avatar")

    # --- Capstone AI Lab (always on) ---
    from blueprints.lab import lab_bp
    app.register_blueprint(lab_bp, url_prefix="/lab")

    from blueprints.stripe_webhook import stripe_webhook_bp
    app.register_blueprint(stripe_webhook_bp, url_prefix="/webhook")

    # --- Context processor ---
    @app.context_processor
    def inject_globals():
        return {
            "business_name": app.config["BUSINESS_NAME"],
            "stripe_checkout_url": app.config["STRIPE_CHECKOUT_URL"],
            "lead_magnet_url": app.config["LEAD_MAGNET_URL"],
            "features": {
                "products":  app.config["FEATURE_PRODUCTS"],
                "clients":   app.config["FEATURE_CLIENTS"],
                "tasks":     app.config["FEATURE_TASKS"],
                "email":     app.config["FEATURE_EMAIL"],
                "analytics": app.config["FEATURE_ANALYTICS"],
                "bookings":  app.config["FEATURE_BOOKINGS"],
                "avatar":    app.config["FEATURE_AVATAR"],
            },
        }

    # --- Create tables & auto-seed on first run ---
    with app.app_context():
        db.create_all()

        # Auto-seed if the database is empty (first run)
        from models import Contact
        if Contact.query.first() is None:
            print("Empty database detected -- seeding demo data...")
            from seed import run_seed
            run_seed()

    return app


# Module-level app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
