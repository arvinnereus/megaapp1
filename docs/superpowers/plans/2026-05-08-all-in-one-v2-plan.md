# All-in-One Business App V2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the All-in-One Business App into a GoHighLevel replacement with unified navigation, AI assistant (Jackie), calendar booking, client onboarding surveys, e-commerce, Umami analytics, Zernio social posting, help/sales playbook, branding, Playwright E2E tests, and Railway deployment — all basic-but-dependable features that students can use and resell tomorrow.

**Two ICPs:**
1. **Resellers (Deidrea-type):** Buy the template, white-label it, sell done-for-you to local businesses ($2k-$5k setup + $97-$300/mo)
2. **Business Owners:** Use it directly to replace GoHighLevel, Calendly, Mailchimp, Shopify subscriptions

**Architecture:** Flask + SQLAlchemy blueprints with feature toggles. Each new feature = new blueprint + model + template. FullCalendar.js for booking (no external accounts), OpenAI provider toggle for Jackie chat, Umami cloud script tag for analytics, Zernio SDK for social posting. Playwright E2E tests. Deploy via Railway CLI.

**Tech Stack:** Flask, SQLAlchemy, Tailwind CSS, Alpine.js, FullCalendar.js, OpenAI API, Umami Cloud, Zernio SDK, Playwright, Railway CLI, PostgreSQL (prod), SQLite (dev)

**Research Summary:**
- Calendar: FullCalendar.js CDN + SQLAlchemy model (no external accounts)
- Umami: One `<script>` tag in base.html, free cloud tier 100K events/mo, Python client `umami-analytics`
- Jackie AI: `openai` package already installed, ~30 line provider toggle in chatbot.py
- Zernio: IS GetLate (rebrand), `pip install zernio-sdk`, 15 platforms supported
- Playwright: `pip install playwright pytest-playwright`, daemon thread fixture
- Railway: `railway up`, MCP server available, zero-downtime deploys

---

## File Structure (New/Modified)

### New Files
```
blueprints/bookings.py          # Calendar booking routes + API
blueprints/onboarding.py        # Client onboarding survey
blueprints/jackie.py            # Jackie AI assistant routes
services/openai_chat.py         # OpenAI/OpenRouter provider toggle
services/zernio.py              # Zernio SDK wrapper (replaces getlate.py)
templates/admin/bookings.html   # Booking calendar page
templates/admin/jackie.html     # Jackie chat full-page
templates/admin/onboarding_list.html  # Survey responses list
templates/public/onboarding.html     # Public survey form
templates/public/store_detail.html   # Product detail expand
templates/help/sell.html        # How to sell this
templates/help/use.html         # How to use this
tests/test_e2e.py               # Playwright E2E tests
tests/conftest_e2e.py           # Playwright fixtures (live_server)
```

### Modified Files
```
app.py                    # New blueprints, new config vars, Umami/branding
models.py                 # Booking, OnboardingSurvey, SurveyResponse models
templates/base.html       # Umami script tag
templates/base_admin.html # Updated sidebar nav (CRM top, Content bottom, Jackie, Manual)
templates/admin/contact_detail.html  # Survey answers + purchases + notes
templates/admin/dashboard.html       # Unified stats
templates/help/index.html            # Two tabs: sell + use
templates/public/store.html          # Product cards with expand
static/css/custom.css     # Animations, polish
.env.example              # New env vars
requirements.txt          # New packages
seed.py                   # More demo data
chatbot.py                # Provider toggle (OpenAI / OpenRouter)
```

---

## Task 1: Update Navigation & Sidebar Layout

**Files:**
- Modify: `templates/base_admin.html`
- Modify: `static/css/custom.css`

- [ ] **Step 1: Read current base_admin.html**

Read `templates/base_admin.html` fully to understand sidebar structure.

- [ ] **Step 2: Restructure sidebar navigation**

Update the sidebar nav in `base_admin.html` to this layout:
```
── CRM ──────────────
  Dashboard
  Contacts
  Deals
  Tasks
  Email
── CONTENT ──────────
  Content Studio
  Products / Store
── TOOLS ────────────
  Bookings
  Jackie AI
  Manual & Help
── SYSTEM ───────────
  Settings
  Logout
```

Group links with section headers. Use `<div class="sidebar-section">` with `<span class="sidebar-label">` for group titles. Keep existing Alpine.js sidebar collapse behavior.

- [ ] **Step 3: Add sidebar section styles to custom.css**

```css
.sidebar-section { margin-top: 1.5rem; }
.sidebar-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  padding: 0 1rem;
  margin-bottom: 0.25rem;
  display: block;
}
```

- [ ] **Step 4: Test sidebar renders on all pages**

Run: `python app.py` and navigate to every sidebar link manually.

- [ ] **Step 5: Commit**

```bash
git add templates/base_admin.html static/css/custom.css
git commit -m "feat: restructure sidebar nav — CRM/Content/Tools/System groups"
```

---

## Task 2: Jackie AI Assistant (OpenAI + OpenRouter Provider Toggle)

**Files:**
- Create: `services/openai_chat.py`
- Create: `blueprints/jackie.py`
- Create: `templates/admin/jackie.html`
- Modify: `chatbot.py`
- Modify: `app.py`
- Modify: `.env.example`

- [ ] **Step 1: Create services/openai_chat.py — provider-agnostic AI client**

```python
"""AI chat provider — supports OpenAI direct and OpenRouter."""
import os
from openai import OpenAI

JACKIE_SYSTEM_PROMPT = """You are Jackie, a friendly and knowledgeable AI business assistant.
You help small business owners with marketing, operations, customer management, and growth strategy.
Keep responses concise and actionable — 2-4 paragraphs max.
Use a warm, professional tone. You're like a smart friend who happens to know business.
If asked about technical setup, guide them step by step.
Always be encouraging — these are hardworking small business owners."""


def get_ai_client():
    """Return (OpenAI client, model_name) based on configured provider."""
    provider = os.getenv("CHAT_PROVIDER", "openrouter")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None, None
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        return client, model
    else:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return None, None
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={"HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000")},
        )
        model = "google/gemini-2.5-flash"
        return client, model


def jackie_chat(user_message, history=None):
    """Send a message to Jackie and get a response."""
    client, model = get_ai_client()
    if not client:
        return {
            "response": "Jackie is not configured yet. Add your OPENAI_API_KEY or OPENROUTER_API_KEY in Settings to activate me!",
            "provider": "demo",
        }

    messages = [{"role": "system", "content": JACKIE_SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-10:])  # last 10 messages for context
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=1024, temperature=0.4
        )
        return {
            "response": response.choices[0].message.content,
            "provider": os.getenv("CHAT_PROVIDER", "openrouter"),
        }
    except Exception as e:
        return {"response": f"Sorry, I hit an error: {str(e)}", "provider": "error"}
```

- [ ] **Step 2: Create blueprints/jackie.py — chat page + API**

```python
"""Jackie AI assistant — full-page chat interface."""
from flask import Blueprint, render_template, request, jsonify
from auth import login_required
from services.openai_chat import jackie_chat

jackie_bp = Blueprint("jackie", __name__)


@jackie_bp.route("/")
@login_required
def index():
    return render_template("admin/jackie.html")


@jackie_bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "Message required"}), 400
    result = jackie_chat(message, history)
    return jsonify(result)
```

- [ ] **Step 3: Create templates/admin/jackie.html — simple chat UI**

Full-page chat interface with Alpine.js. Clean, simple design — message bubbles, input bar at bottom, auto-scroll. Uses the existing dark theme from custom.css. Chat history persisted in localStorage.

Key elements:
- Chat messages area with user/assistant bubbles
- Input bar with send button at bottom
- "Jackie" header with status indicator (connected/demo mode)
- Clear history button

- [ ] **Step 4: Register jackie_bp in app.py**

```python
from blueprints.jackie import jackie_bp
app.register_blueprint(jackie_bp, url_prefix="/jackie")
```

Add config vars:
```python
app.config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
app.config["CHAT_PROVIDER"] = os.environ.get("CHAT_PROVIDER", "openrouter")
```

- [ ] **Step 5: Add env vars to .env.example**

```
# Jackie AI Assistant
OPENAI_API_KEY=sk-your-openai-key-here
CHAT_PROVIDER=openrouter          # "openai" or "openrouter"
OPENAI_CHAT_MODEL=gpt-4o-mini    # or gpt-4o for higher quality
```

- [ ] **Step 6: Test Jackie chat**

Run app, navigate to /jackie, send a message, verify response.

- [ ] **Step 7: Commit**

```bash
git add services/openai_chat.py blueprints/jackie.py templates/admin/jackie.html app.py .env.example
git commit -m "feat: add Jackie AI assistant with OpenAI/OpenRouter provider toggle"
```

---

## Task 3: Calendar Booking System

**Files:**
- Modify: `models.py` — add Booking, BookingSlot models
- Create: `blueprints/bookings.py`
- Create: `templates/admin/bookings.html`
- Create: `templates/public/book.html`
- Modify: `app.py`

- [ ] **Step 1: Add Booking models to models.py**

```python
class BookingSlot(db.Model):
    """Available time slots configured by the business owner."""
    __tablename__ = "booking_slots"
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = db.Column(db.String(5), nullable=False)  # "09:00"
    end_time = db.Column(db.String(5), nullable=False)    # "10:00"
    slot_type = db.Column(db.String(50), default="consultation")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Booking(db.Model):
    """A confirmed appointment."""
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(30), default="")
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    slot_type = db.Column(db.String(50), default="consultation")
    status = db.Column(db.String(20), default="confirmed")  # confirmed/cancelled/completed
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=db.func.now())
    contact = db.relationship("Contact", backref="bookings")
```

- [ ] **Step 2: Create blueprints/bookings.py**

Routes:
- `GET /bookings/` — admin calendar view (FullCalendar.js showing all bookings)
- `GET /bookings/api/events` — JSON feed for FullCalendar (returns bookings as calendar events)
- `GET /bookings/api/available?date=YYYY-MM-DD` — returns available slots for a given date
- `POST /bookings/api/book` — create a booking (public, no auth — for clients)
- `PATCH /bookings/api/<id>/status` — update booking status (admin, auth required)
- `GET /book` — public booking page (no auth, embeddable)
- Admin routes for managing slots (CRUD)

- [ ] **Step 3: Create templates/admin/bookings.html**

Admin calendar page using FullCalendar.js via CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.17/index.global.min.js"></script>
```

Calendar loads events from `/bookings/api/events`. Click on event to see details. Sidebar panel for managing available slots (add/remove time slots per day of week).

- [ ] **Step 4: Create templates/public/book.html**

Public-facing booking form:
- Date picker showing available dates
- Time slot selector (filtered by availability)
- Name, email, phone fields
- Submit creates booking + optionally creates Contact in CRM
- Confirmation message after booking

- [ ] **Step 5: Register bookings_bp in app.py with feature toggle**

```python
app.config["FEATURE_BOOKINGS"] = os.environ.get("FEATURE_BOOKINGS", "true").lower() == "true"

if app.config["FEATURE_BOOKINGS"]:
    from blueprints.bookings import bookings_bp
    app.register_blueprint(bookings_bp, url_prefix="/bookings")
```

- [ ] **Step 6: Add demo booking data to seed.py**

Add 5 BookingSlots (Mon-Fri 9am-5pm hourly) and 3 sample Bookings.

- [ ] **Step 7: Test booking flow end-to-end**

- [ ] **Step 8: Commit**

```bash
git add models.py blueprints/bookings.py templates/admin/bookings.html templates/public/book.html app.py seed.py
git commit -m "feat: add calendar booking system with FullCalendar.js"
```

---

## Task 4: Client Onboarding Survey

**Files:**
- Modify: `models.py` — add OnboardingSurvey, SurveyResponse models
- Create: `blueprints/onboarding.py`
- Create: `templates/public/onboarding.html`
- Create: `templates/admin/onboarding_list.html`
- Modify: `templates/admin/contact_detail.html`

- [ ] **Step 1: Add survey models to models.py**

```python
class SurveyQuestion(db.Model):
    """Configurable survey questions."""
    __tablename__ = "survey_questions"
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), default="text")  # text/select/textarea
    options = db.Column(db.Text, default="")  # JSON for select options
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

class SurveyResponse(db.Model):
    """A completed survey submission."""
    __tablename__ = "survey_responses"
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=True)
    respondent_name = db.Column(db.String(100), nullable=False)
    respondent_email = db.Column(db.String(120), nullable=False)
    answers = db.Column(db.Text, default="{}")  # JSON dict of question_id: answer
    submitted_at = db.Column(db.DateTime, default=db.func.now())
    contact = db.relationship("Contact", backref="survey_responses")
```

- [ ] **Step 2: Create blueprints/onboarding.py**

Routes:
- `GET /onboarding/` — public survey form (no auth)
- `POST /onboarding/submit` — submit survey, create/link Contact, redirect to thank-you
- `GET /onboarding/admin` — admin list of responses (auth required)
- `GET /onboarding/admin/questions` — manage survey questions (auth required)
- API routes for CRUD on questions

- [ ] **Step 3: Create templates/public/onboarding.html**

Clean public form with questions rendered dynamically from SurveyQuestion records. Fields: name, email, phone, business name, then survey questions. Styled to match the public landing page theme.

- [ ] **Step 4: Update contact_detail.html to show survey answers**

Add a "Survey Responses" section to the contact detail page showing all survey answers for that contact. Also show "Products Purchased" section from the purchases relationship.

- [ ] **Step 5: Add default survey questions to seed.py**

```python
default_questions = [
    "What is your business name?",
    "What industry are you in?",
    "How many employees do you have?",
    "What is your biggest challenge right now?",
    "What tools/software are you currently using?",
    "What is your monthly marketing budget?",
    "How did you hear about us?",
]
```

- [ ] **Step 6: Register onboarding_bp in app.py**

- [ ] **Step 7: Test survey flow — submit, verify contact created, view in admin**

- [ ] **Step 8: Commit**

```bash
git add models.py blueprints/onboarding.py templates/public/onboarding.html templates/admin/onboarding_list.html templates/admin/contact_detail.html seed.py app.py
git commit -m "feat: add client onboarding survey linked to CRM contacts"
```

---

## Task 5: E-Commerce Store Upgrade (Product Detail + Expand)

**Files:**
- Modify: `templates/public/store.html`
- Modify: `static/css/custom.css`

- [ ] **Step 1: Read current store.html**

- [ ] **Step 2: Upgrade store.html with expandable product cards**

Each product card shows: image, name, price, short description. On click, expands inline (Alpine.js `x-show` with slide transition) to show full description + "Buy Now" button. Simple, clean — 3 products in a row on desktop, stacked on mobile.

Add Alpine.js expand/collapse with smooth animation:
```html
<div x-data="{ expanded: false }" @click="expanded = !expanded">
  <!-- Card content -->
  <div x-show="expanded" x-transition.duration.300ms>
    <!-- Full description + buy button -->
  </div>
</div>
```

- [ ] **Step 3: Add subtle CSS animations**

```css
.product-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-gold);
}
```

- [ ] **Step 4: Test store page with demo products**

- [ ] **Step 5: Commit**

```bash
git add templates/public/store.html static/css/custom.css
git commit -m "feat: upgrade store with expandable product cards and hover effects"
```

---

## Task 6: Umami Analytics Integration

**Files:**
- Modify: `templates/base.html`
- Modify: `app.py`
- Modify: `.env.example`

- [ ] **Step 1: Add Umami script tag to base.html**

Add inside `<head>`:
```html
{% if config.UMAMI_WEBSITE_ID %}
<script defer src="{{ config.UMAMI_SCRIPT_URL | default('https://cloud.umami.is/script.js') }}"
        data-website-id="{{ config.UMAMI_WEBSITE_ID }}"></script>
{% endif %}
```

- [ ] **Step 2: Add config vars to app.py**

```python
app.config["UMAMI_WEBSITE_ID"] = os.environ.get("UMAMI_WEBSITE_ID", "")
app.config["UMAMI_SCRIPT_URL"] = os.environ.get("UMAMI_SCRIPT_URL", "https://cloud.umami.is/script.js")
```

- [ ] **Step 3: Add to .env.example**

```
# Umami Analytics (free at umami.is)
UMAMI_WEBSITE_ID=
UMAMI_SCRIPT_URL=https://cloud.umami.is/script.js
```

- [ ] **Step 4: Commit**

```bash
git add templates/base.html app.py .env.example
git commit -m "feat: add Umami analytics tracking script"
```

---

## Task 7: Zernio SDK Integration (Replace GetLate)

**Files:**
- Create: `services/zernio.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `blueprints/content_api.py` (update publish route)

- [ ] **Step 1: Create services/zernio.py**

Wrapper around zernio-sdk:
```python
"""Social media publishing via Zernio (formerly GetLate.dev)."""
import os

def publish_post(content_item, platforms=None, emit_event=None):
    api_key = os.getenv("ZERNIO_API_KEY") or os.getenv("GETLATE_API_KEY", "")
    if not api_key:
        # Demo mode
        return {"status": "demo", "post_id": "demo-123", "platforms": platforms or ["demo"]}

    try:
        from zernio import Zernio
        client = Zernio(api_key=api_key)
        # Build post from content_item
        accounts = client.accounts.list()
        # Match platforms to connected accounts
        # Create post with content and media
        # Return result
    except ImportError:
        # Fallback to existing getlate.py if zernio-sdk not installed
        from services.getlate import publish_post as legacy_publish
        return legacy_publish(content_item, platforms, emit_event)


def get_connected_accounts():
    api_key = os.getenv("ZERNIO_API_KEY") or os.getenv("GETLATE_API_KEY", "")
    if not api_key:
        return {"demo": [{"platform": "instagram", "name": "Demo Account"}]}
    try:
        from zernio import Zernio
        client = Zernio(api_key=api_key)
        return client.accounts.list()
    except ImportError:
        from services.getlate import get_connected_accounts as legacy_get
        return legacy_get()
```

- [ ] **Step 2: Add zernio-sdk to requirements.txt**

```
zernio-sdk>=0.1
```

- [ ] **Step 3: Update .env.example**

```
# Social Media Publishing (Zernio — formerly GetLate.dev)
ZERNIO_API_KEY=sk_your-zernio-api-key
```

- [ ] **Step 4: Update content_api.py publish route to use zernio.py**

- [ ] **Step 5: Commit**

```bash
git add services/zernio.py requirements.txt .env.example blueprints/content_api.py
git commit -m "feat: add Zernio SDK integration for social media publishing"
```

---

## Task 8: Help & Sales Playbook

**Files:**
- Create: `templates/help/sell.html`
- Create: `templates/help/use.html`
- Modify: `templates/help/index.html`
- Modify: `blueprints/help.py`

- [ ] **Step 1: Update blueprints/help.py with tab routes**

```python
@help_bp.route("/")
@login_required
def index():
    return render_template("help/index.html", tab="use")

@help_bp.route("/sell")
@login_required
def sell():
    return render_template("help/index.html", tab="sell")
```

- [ ] **Step 2: Rebuild templates/help/index.html with two tabs**

Tab 1 — "How to Use This" (for business owners):
- Quick Start Guide (5 steps)
- Feature overview with screenshots placeholders
- API key setup walkthrough
- Common workflows (add contact, create content, book appointment)

Tab 2 — "How to Sell This" (for resellers like Deidrea):
- Pricing packages:
  - Starter ($2,000 setup + $97/mo) — Website + CRM + Calendar
  - Professional ($3,500 setup + $197/mo) — + Content Automation + Email
  - Enterprise ($5,000 setup + $297/mo) — + AI Assistant + Analytics + Custom
- Sales script outline
- Client onboarding checklist
- Upsell opportunities (bolt-ons: SEO, ads, content analytics)
- Links to simpletechskills.com/coaching ($500/mo) and /academy ($7/mo)

- [ ] **Step 3: Add branding footer**

Include in the help page and throughout the app:
```
Powered by Dr.AI | Built with Simple Tech Skills
simpletechskills.com/coaching | simpletechskills.com/academy
```

- [ ] **Step 4: Commit**

```bash
git add blueprints/help.py templates/help/
git commit -m "feat: add Help tabs — How to Use + How to Sell with pricing packages"
```

---

## Task 9: Branding & Licensing

**Files:**
- Modify: `templates/base_admin.html`
- Modify: `templates/base.html`
- Modify: `static/css/custom.css`

- [ ] **Step 1: Add persistent branding to base_admin.html**

At the bottom of the sidebar:
```html
<div class="sidebar-branding">
  <span class="brand-badge">Powered by Dr.AI</span>
  <a href="https://simpletechskills.com/coaching" target="_blank">SimpleTechSkills</a>
</div>
```

Style it small, subtle, but not easily removable (embedded in the base template structure).

- [ ] **Step 2: Add license comment to base.html**

```html
<!-- Licensed by Simple Tech Skills | simpletechskills.com
     Resale license required for commercial redistribution.
     Contact: simpletechskills.com/coaching -->
```

- [ ] **Step 3: Add branding CSS**

```css
.sidebar-branding {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.65rem;
  color: var(--text-tertiary);
}
.brand-badge {
  display: block;
  color: var(--gold);
  font-weight: 600;
  margin-bottom: 0.25rem;
}
```

- [ ] **Step 4: Commit**

```bash
git add templates/base_admin.html templates/base.html static/css/custom.css
git commit -m "feat: add Dr.AI branding and SimpleTechSkills licensing"
```

---

## Task 10: CSS Polish & Animations

**Files:**
- Modify: `static/css/custom.css`

- [ ] **Step 1: Add subtle page transition animations**

```css
/* Fade-in on page load */
.main-content { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* Stat cards hover */
.stat-card { transition: transform 0.2s, box-shadow 0.2s; }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-gold); }

/* Button press effect */
.btn-primary:active { transform: scale(0.97); }

/* Smooth sidebar transitions */
.sidebar-link { transition: background 0.15s, color 0.15s, padding-left 0.15s; }
.sidebar-link:hover { padding-left: 1.25rem; }
```

- [ ] **Step 2: Add toast notification animation**

```css
.toast {
  animation: slideInRight 0.3s ease-out;
}
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

- [ ] **Step 3: Commit**

```bash
git add static/css/custom.css
git commit -m "feat: add CSS animations — fade-in, hover effects, toast slides"
```

---

## Task 11: Enhanced Seed Data & Strong Auth

**Files:**
- Modify: `seed.py`
- Modify: `.env.example`

- [ ] **Step 1: Add more demo data to seed.py**

Add:
- 5 BookingSlots (Mon-Fri, 9am-12pm hourly)
- 3 sample Bookings (past and future)
- 7 default SurveyQuestions
- 2 sample SurveyResponses linked to existing contacts
- 2 more Products (coaching session $197, monthly retainer $297)
- More varied contacts with different statuses

- [ ] **Step 2: Update .env.example with strong defaults**

```
ADMIN_USER=instructor
ADMIN_PASS=SaturdayWorkshop2026!
```

- [ ] **Step 3: Commit**

```bash
git add seed.py .env.example
git commit -m "feat: expand seed data — bookings, surveys, products; strong default password"
```

---

## Task 12: Playwright E2E Tests

**Files:**
- Create: `tests/test_e2e.py`
- Modify: `tests/conftest.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add playwright to requirements.txt**

```
playwright>=1.40
pytest-playwright>=0.5
```

- [ ] **Step 2: Add live_server fixture to tests/conftest.py**

Add the daemon thread pattern:
- `_find_free_port()` — finds available port
- `live_server` fixture (session-scoped) — starts Flask on random port with in-memory SQLite
- `authenticated_page` fixture — logs in and returns page
- Set ADMIN_USER=admin, ADMIN_PASS=testpass123

- [ ] **Step 3: Create tests/test_e2e.py with core user flows**

```python
"""E2E tests — run with: pytest tests/test_e2e.py -v --headed --slowmo 500"""

def test_login_flow(page, live_server):
    """Login with valid credentials reaches dashboard."""

def test_unauthenticated_redirect(page, live_server):
    """Protected pages redirect to login."""

def test_dashboard_loads(authenticated_page, live_server):
    """Dashboard shows KPI stats."""

def test_contacts_page(authenticated_page, live_server):
    """Contacts page loads and shows search."""

def test_content_page(authenticated_page, live_server):
    """Content studio page loads."""

def test_jackie_page(authenticated_page, live_server):
    """Jackie AI page loads with chat input."""

def test_bookings_page(authenticated_page, live_server):
    """Bookings page loads with calendar."""

def test_settings_page(authenticated_page, live_server):
    """Settings page loads with API key fields."""

def test_public_landing(page, live_server):
    """Landing page loads without auth."""

def test_public_store(page, live_server):
    """Store page loads without auth."""

def test_public_booking(page, live_server):
    """Public booking page loads without auth."""

def test_onboarding_form(page, live_server):
    """Onboarding survey form loads and submits."""
```

- [ ] **Step 4: Run tests**

```bash
pip install playwright pytest-playwright
playwright install chromium
pytest tests/test_e2e.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e.py tests/conftest.py requirements.txt
git commit -m "feat: add Playwright E2E tests for all core user flows"
```

---

## Task 13: Update requirements.txt & .env.example (Final)

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Ensure all new packages in requirements.txt**

```
# Add these to existing requirements.txt:
zernio-sdk>=0.1
playwright>=1.40
pytest-playwright>=0.5
```

- [ ] **Step 2: Ensure all new env vars in .env.example with descriptions**

```
# ── Jackie AI Assistant ──
OPENAI_API_KEY=sk-your-openai-key
CHAT_PROVIDER=openrouter
OPENAI_CHAT_MODEL=gpt-4o-mini

# ── Umami Analytics ──
UMAMI_WEBSITE_ID=
UMAMI_SCRIPT_URL=https://cloud.umami.is/script.js

# ── Social Media (Zernio) ──
ZERNIO_API_KEY=sk_your-zernio-key

# ── Feature Toggles ──
FEATURE_BOOKINGS=true

# ── Auth (use strong password!) ──
ADMIN_USER=instructor
ADMIN_PASS=SaturdayWorkshop2026!
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: finalize requirements and env example for V2"
```

---

## Task 14: Railway Deployment

- [ ] **Step 1: Deploy to Railway**

```bash
railway login
railway init -n "all-in-one-business-app"
railway add --database postgres
railway service  # select app service
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
railway variables set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
railway variables set ADMIN_USER="instructor"
railway variables set ADMIN_PASS="SaturdayWorkshop2026!"
railway variables set BUSINESS_NAME="All-in-One Business App"
railway variables set FEATURE_PRODUCTS="true"
railway variables set FEATURE_CLIENTS="true"
railway variables set FEATURE_TASKS="true"
railway variables set FEATURE_EMAIL="true"
railway variables set FEATURE_ANALYTICS="true"
railway variables set FEATURE_BOOKINGS="true"
railway up
railway domain
```

- [ ] **Step 2: Verify deployment**

Open the Railway URL and test login, dashboard, all sidebar links.

- [ ] **Step 3: Commit any deployment fixes**

---

## Future Roadmap (V3+)

These are deferred to future iterations:

- [ ] OpenAI Realtime Voice (orb UI from docs/OPENAI_REALTIME_VOICE_SETUP.md)
- [ ] Twilio SMS integration for booking confirmations
- [ ] Multi-tenant architecture (GoHighLevel-style sub-accounts with Supabase)
- [ ] PWA wrapper for mobile app experience
- [ ] Google Workspace email integration (free 2K emails/day)
- [ ] Client document management with R2 storage
- [ ] Content analytics dashboard (pull Umami data via API)
- [ ] Custom domain per client (Railway custom domains)
- [ ] Stripe subscription billing for tiers ($97/$197/$297)
- [ ] Print/export PDF reports
- [ ] SOP documentation system (rich text editor per client)
- [ ] Facebook Ads integration (Meta API)
- [ ] SEO/AEO optimization tools
- [ ] White-label admin panel (custom logos, colors per tenant)
- [ ] Advanced email sequences (drip campaigns, triggers)
- [ ] Team roles and permissions (admin/editor/viewer)
- [ ] Zapier/webhook integrations
