# All-in-One Business App

## Project Overview
A Flask app that merges a CRM and Content Automation system into a single deployable product.
Built for the Saturday Workshop as a live coding demo and reusable starting point.

## Tech Stack
- **Backend:** Flask + SQLAlchemy
- **Frontend:** Tailwind CSS + Alpine.js
- **Database:** SQLite (dev) / PostgreSQL (production via Railway)
- **AI:** OpenRouter (Claude, GPT-4)
- **Storage:** Cloudflare R2
- **Email:** Resend
- **Payments:** Stripe

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python app.py          # runs on http://localhost:8000
```

## Testing
```bash
python -m pytest tests/ -v
```

## Deploy
Railway with a PostgreSQL plugin. Set all env vars from `.env.example` in the Railway dashboard.
`railway.toml` handles the build and start command automatically.

## Project Structure
```
app.py                  # Flask factory — registers all blueprints
extensions.py           # Shared SQLAlchemy db instance
auth.py                 # login_required decorator + check_credentials
blueprints/             # One file per feature area (routes only)
  public.py             # Marketing / landing pages
  admin.py              # Dashboard login/logout
  api.py                # JSON API endpoints (CRM)
  content.py            # Content automation UI
  content_api.py        # Content automation JSON endpoints
  help.py               # Interactive help / onboarding
  products.py           # Product catalog (FEATURE_PRODUCTS)
  clients.py            # Client management (FEATURE_CLIENTS)
  tasks.py              # Task tracker (FEATURE_TASKS)
  email.py              # Email campaigns (FEATURE_EMAIL)
services/               # Third-party API wrappers (no Flask imports)
  openrouter.py         # AI text generation
  firecrawl.py          # Web scraping
  kie_ai.py             # Image generation
  resend.py             # Transactional email
  stripe_service.py     # Payments
  r2.py                 # File storage
templates/              # Jinja2 HTML templates
static/                 # CSS, JS, images
tests/                  # pytest test suite
```

## Key Patterns
- **Feature toggles** — blueprints are only registered if the matching `FEATURE_*` env var is `"true"`.
- **login_required** — import from `auth.py` and decorate any route that needs auth.
- **SQLAlchemy models** — define in `models.py` (or split per domain), import `db` from `extensions.py`.
- **SSE streaming** — use `flask.Response` with `mimetype="text/event-stream"` for real-time AI output.
- **postgres:// fix** — `app.py` automatically rewrites legacy Railway URLs to `postgresql://`.

## Environment Variables
See `.env.example` for the full list with descriptions.
