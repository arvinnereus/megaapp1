# All-in-One Business App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge CRM Demo + Content Automation Demo into a single Flask app with unified database, auth, navigation, and an interactive help page.

**Architecture:** Blueprint Merge — one Flask app factory, SQLAlchemy ORM for all models, left sidebar navigation. Content Automation's raw SQLite models are ported to SQLAlchemy. Services and pipeline are adapted to use the ORM. Kie.ai polling is made more patient (30s intervals, 15min video timeout).

**Tech Stack:** Flask 3.x, SQLAlchemy 2.x, Tailwind CSS (CDN), Alpine.js (CDN), Gunicorn, PostgreSQL (prod) / SQLite (dev)

**Source Reference:**
- CRM: `CRM Demo For Claude Workshop/` (copy patterns from here)
- Content: `Content Automation Demo For Claude Workshop/` (port code from here)
- Output: Root of repo (new unified app)

---

## File Map

### Create (new unified app at repo root)
```
app.py                    # Flask factory — merge both apps' config
extensions.py             # db = SQLAlchemy()
models.py                 # All 14 models (11 CRM + 3 Content)
auth.py                   # Login decorator (from CRM)
chatbot.py                # AI chatbot (from CRM)
pipeline.py               # Content pipeline (ported from Content, uses SQLAlchemy)
seed.py                   # Demo data for CRM + Content

blueprints/
  __init__.py
  public.py               # From CRM
  admin.py                # From CRM (dashboard updated with content stats)
  api.py                  # From CRM
  content.py              # NEW — content pages + SSE streaming
  content_api.py          # NEW — content JSON API
  products.py             # From CRM
  clients.py              # From CRM
  tasks.py                # From CRM
  email.py                # From CRM
  help.py                 # NEW — interactive help page

services/
  __init__.py
  openrouter.py           # From Content (as-is)
  kie_ai.py               # From Content (patient polling fix)
  firecrawl.py            # From Content (as-is)
  getlate.py              # From Content (as-is)
  r2_storage.py           # From Content (as-is)

templates/
  base.html               # Merged — Tailwind + Alpine + toast system
  base_admin.html          # Merged — left sidebar with all 6 nav items
  admin/
    login.html            # From CRM
    dashboard.html        # Modified — add content stats section
    contacts.html         # From CRM
    contact_detail.html   # From CRM
    deals.html            # From CRM
    clients.html          # From CRM (if FEATURE_CLIENTS)
    client_detail.html    # From CRM (if FEATURE_CLIENTS)
    products.html         # From CRM (if FEATURE_PRODUCTS)
    product_detail.html   # From CRM (if FEATURE_PRODUCTS)
    tasks.html            # From CRM (if FEATURE_TASKS)
    email_templates.html  # From CRM (if FEATURE_EMAIL)
    email_log.html        # From CRM (if FEATURE_EMAIL)
  content/
    index.html            # Content list/queue (from Content dashboard.html)
    create.html           # Create form (from Content cam.html, simplified)
    detail.html           # Content detail with X-ray (from Content content_detail.html)
  help/
    index.html            # NEW — interactive walkthrough
  public/
    landing.html          # From CRM
    thank_you.html        # From CRM
    sales.html            # From CRM
    store.html            # From CRM (if FEATURE_PRODUCTS)
    checkout_success.html # From CRM (if FEATURE_PRODUCTS)
    checkout_cancel.html  # From CRM (if FEATURE_PRODUCTS)

static/
  css/custom.css          # From CRM (dark gold design system)
  js/
    chat.js               # From CRM
    pipeline.js           # NEW — SSE pipeline visualization (extracted from Content cam.html)

tests/
  conftest.py             # Unified fixtures
  test_api.py             # CRM API tests
  test_auth.py            # Auth tests
  test_content.py         # NEW — content pipeline tests
  test_content_api.py     # NEW — content API tests
  test_help.py            # NEW — help page tests

.env.example              # Unified env config
requirements.txt          # Merged dependencies
Procfile                  # Gunicorn config
railway.toml              # Railway deployment
CLAUDE.md                 # Project documentation
```

---

## Task 1: Core App Scaffold

**Files:**
- Create: `app.py`, `extensions.py`, `auth.py`, `requirements.txt`, `.env.example`, `Procfile`, `railway.toml`, `CLAUDE.md`

- [ ] **Step 1: Create `extensions.py`**

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

- [ ] **Step 2: Create `auth.py`**

Copy from `CRM Demo For Claude Workshop/auth.py` exactly — it's already clean.

- [ ] **Step 3: Create `app.py`**

Flask factory that registers all blueprints. Merge config from both apps:

```python
import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db

load_dotenv()


def create_app():
    app = Flask(__name__)

    # --- Config ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
            "SQLALCHEMY_DATABASE_URI"
        ].replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Admin
    app.config["ADMIN_USER"] = os.getenv("ADMIN_USER", "admin")
    app.config["ADMIN_PASS"] = os.getenv("ADMIN_PASS", "admin")
    app.config["BUSINESS_NAME"] = os.getenv("BUSINESS_NAME", "All-in-One Business App")

    # CRM integrations
    app.config["STRIPE_CHECKOUT_URL"] = os.getenv("STRIPE_CHECKOUT_URL", "#")
    app.config["LEAD_MAGNET_URL"] = os.getenv("LEAD_MAGNET_URL", "#")
    app.config["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")

    # Content integrations (all optional — demo mode if unset)
    app.config["FIRECRAWL_API_KEY"] = os.getenv("FIRECRAWL_API_KEY", "")
    app.config["KIE_AI_API_KEY"] = os.getenv("KIE_AI_API_KEY", "")
    app.config["GETLATE_API_KEY"] = os.getenv("GETLATE_API_KEY", "")

    # Feature toggles
    app.config["FEATURE_PRODUCTS"] = os.getenv("FEATURE_PRODUCTS", "true")
    app.config["FEATURE_CLIENTS"] = os.getenv("FEATURE_CLIENTS", "true")
    app.config["FEATURE_TASKS"] = os.getenv("FEATURE_TASKS", "true")
    app.config["FEATURE_EMAIL"] = os.getenv("FEATURE_EMAIL", "true")
    app.config["FEATURE_ANALYTICS"] = os.getenv("FEATURE_ANALYTICS", "true")

    # Init extensions
    db.init_app(app)

    # --- Core blueprints (always active) ---
    from blueprints.public import public_bp
    from blueprints.admin import admin_bp
    from blueprints.api import api_bp
    from blueprints.content import content_bp
    from blueprints.content_api import content_api_bp
    from blueprints.help import help_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(content_bp, url_prefix="/content")
    app.register_blueprint(content_api_bp, url_prefix="/content/api")
    app.register_blueprint(help_bp, url_prefix="/help")

    # --- Feature blueprints (togglable) ---
    if app.config["FEATURE_PRODUCTS"] == "true":
        from blueprints.products import products_bp
        app.register_blueprint(products_bp)

    if app.config["FEATURE_CLIENTS"] == "true":
        from blueprints.clients import clients_bp
        app.register_blueprint(clients_bp)

    if app.config["FEATURE_TASKS"] == "true":
        from blueprints.tasks import tasks_bp
        app.register_blueprint(tasks_bp)

    if app.config["FEATURE_EMAIL"] == "true":
        from blueprints.email import email_bp
        app.register_blueprint(email_bp)

    # Template globals
    @app.context_processor
    def inject_globals():
        return {
            "business_name": app.config["BUSINESS_NAME"],
            "stripe_checkout_url": app.config["STRIPE_CHECKOUT_URL"],
            "lead_magnet_url": app.config["LEAD_MAGNET_URL"],
            "features": {
                "products": app.config["FEATURE_PRODUCTS"] == "true",
                "clients": app.config["FEATURE_CLIENTS"] == "true",
                "tasks": app.config["FEATURE_TASKS"] == "true",
                "email": app.config["FEATURE_EMAIL"] == "true",
                "analytics": app.config["FEATURE_ANALYTICS"] == "true",
            },
        }

    # Create tables
    with app.app_context():
        import models  # noqa: F401
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
```

- [ ] **Step 4: Create `requirements.txt`**

```
flask>=3.1
flask-sqlalchemy>=3.1
sqlalchemy>=2.0
psycopg2-binary>=2.9
gunicorn>=22.0
python-dotenv>=1.0
requests>=2.32
openai>=1.0
firecrawl-py>=1.0
boto3>=1.34
pytest>=8.0
```

- [ ] **Step 5: Create `.env.example`**

Unified env file with all CRM + Content vars. See spec for full list.

- [ ] **Step 6: Create `Procfile`**

```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --preload
```

- [ ] **Step 7: Create `railway.toml`**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --preload"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

- [ ] **Step 8: Create `CLAUDE.md`**

Project overview doc explaining the unified app, how to run it, test it, deploy it.

- [ ] **Step 9: Create `blueprints/__init__.py`** and `services/__init__.py`**

Empty init files.

---

## Task 2: Unified Models

**Files:**
- Create: `models.py`

Port all 11 CRM models from `CRM Demo For Claude Workshop/models.py` plus 3 new Content models (ContentItem, PipelineLog, Setting) converted from raw SQLite to SQLAlchemy.

- [ ] **Step 1: Create `models.py` with all CRM models**

Copy Contact, Deal, Note, ActivityLog, Product, Purchase, ClientNote, Task, EmailTemplate, EmailLog, PageView, and the `log_activity()` helper from the CRM's models.py.

- [ ] **Step 2: Add ContentItem model**

```python
class ContentItem(db.Model):
    __tablename__ = "content_items"

    id = db.Column(db.Integer, primary_key=True)
    input_text = db.Column(db.Text)
    input_type = db.Column(db.String(10), default="idea")  # 'url' or 'idea'
    platform = db.Column(db.String(20), default="tiktok")
    article_text = db.Column(db.Text)
    article_title = db.Column(db.String(500))
    word_count = db.Column(db.Integer)
    script = db.Column(db.Text)
    image_prompt = db.Column(db.Text)
    image_url = db.Column(db.Text)
    image_task_id = db.Column(db.String(100))
    video_prompt = db.Column(db.Text)
    video_url = db.Column(db.Text)
    video_task_id = db.Column(db.String(100))
    captions = db.Column(db.Text)  # JSON string
    include_video = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="draft")
    cost_total = db.Column(db.Float, default=0.0)
    stage_durations = db.Column(db.Text)  # JSON string
    stage_costs = db.Column(db.Text)  # JSON string
    r2_image_url = db.Column(db.Text)
    r2_video_url = db.Column(db.Text)
    scheduled_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pipeline_logs = db.relationship("PipelineLog", backref="content_item", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "input_text": self.input_text,
            "input_type": self.input_type,
            "platform": self.platform,
            "article_title": self.article_title,
            "script": self.script,
            "image_url": self.image_url,
            "video_url": self.video_url,
            "captions": self.captions,
            "include_video": self.include_video,
            "status": self.status,
            "cost_total": self.cost_total,
            "stage_durations": self.stage_durations,
            "stage_costs": self.stage_costs,
            "r2_image_url": self.r2_image_url,
            "r2_video_url": self.r2_video_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 3: Add PipelineLog model**

```python
class PipelineLog(db.Model):
    __tablename__ = "pipeline_logs"

    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    stage = db.Column(db.String(30))
    status = db.Column(db.String(20))  # progress, error, polling, success
    message = db.Column(db.Text)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "content_id": self.content_id,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Add Setting model**

```python
class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        s = Setting.query.get(key)
        return s.value if s else default

    @staticmethod
    def set(key, value):
        s = Setting.query.get(key)
        if s:
            s.value = value
        else:
            s = Setting(key=key, value=value)
            db.session.add(s)
        db.session.commit()
```

- [ ] **Step 5: Verify models compile**

Run: `python -c "from models import *; print('OK')"` (will fail until app.py is wired, but checks syntax)

---

## Task 3: Services Layer

**Files:**
- Create: `services/openrouter.py`, `services/kie_ai.py`, `services/firecrawl.py`, `services/getlate.py`, `services/r2_storage.py`

- [ ] **Step 1: Copy `services/openrouter.py`**

Copy from `Content Automation Demo For Claude Workshop/services/openrouter.py` as-is. No changes needed.

- [ ] **Step 2: Copy `services/firecrawl.py`**

Copy from `Content Automation Demo For Claude Workshop/services/firecrawl.py` as-is.

- [ ] **Step 3: Copy `services/getlate.py`**

Copy from `Content Automation Demo For Claude Workshop/services/getlate.py` as-is.

- [ ] **Step 4: Copy `services/r2_storage.py`**

Copy from `Content Automation Demo For Claude Workshop/services/r2_storage.py` as-is.

- [ ] **Step 5: Copy and fix `services/kie_ai.py` — Patient Polling**

Copy from `Content Automation Demo For Claude Workshop/services/kie_ai.py` and modify the polling constants:

**Image polling** — change from 2s/120s to 5s/180s:
```python
# In generate_image() polling loop:
POLL_INTERVAL = 5      # was 2
MAX_POLL_TIME = 180    # was 120 (3 minutes)
```

**Video polling** — change from 20s/600s to patient two-phase:
```python
# In generate_video() polling loop:
PHASE_1_INTERVAL = 30    # was 20 — poll every 30s
PHASE_1_DURATION = 300   # first 5 minutes
PHASE_2_INTERVAL = 60    # then every 60s
MAX_POLL_TIME = 900      # 15 minutes total
```

Replace the single polling loop with two-phase polling:
```python
elapsed = 0
while elapsed < MAX_POLL_TIME:
    if elapsed < PHASE_1_DURATION:
        interval = PHASE_1_INTERVAL
    else:
        interval = PHASE_2_INTERVAL
    time.sleep(interval)
    elapsed += interval
    # ... existing poll logic ...
    if emit:
        phase = "Phase 1" if elapsed < PHASE_1_DURATION else "Phase 2 (patient)"
        emit("video", "polling", f"{phase} — Attempt #{attempt}... Kie.ai says: {state}", ...)
```

On timeout, log a clear message but DON'T raise an exception — return a result with `"timed_out": True` so the pipeline can continue:
```python
if elapsed >= MAX_POLL_TIME:
    return {
        "video_url": None,
        "timed_out": True,
        "message": "Video generation timed out after 15 minutes. Kie.ai may still be processing — check back later.",
        "task_id": task_id,
        "cost": cost,
    }
```

---

## Task 4: Pipeline (ported to SQLAlchemy)

**Files:**
- Create: `pipeline.py`

- [ ] **Step 1: Port `pipeline.py` from Content Automation**

Copy from `Content Automation Demo For Claude Workshop/pipeline.py` and replace ALL raw SQLite calls with SQLAlchemy:

Key changes:
- Replace `from models import get_db, update_content_item` with `from models import ContentItem, PipelineLog, Setting` and `from extensions import db`
- Replace `update_content_item(content_id, ...)` with:
  ```python
  item = ContentItem.query.get(content_id)
  item.status = "scripted"
  item.script = script
  db.session.commit()
  ```
- Replace `_log_event(content_id, ...)` with:
  ```python
  log = PipelineLog(content_id=content_id, stage=stage, status=status, message=message, detail=detail)
  db.session.add(log)
  db.session.commit()
  ```
- Replace `get_setting("key")` with `Setting.get("key")`
- Keep the SSE emit pattern and stage_durations/stage_costs JSON tracking
- Keep the `run_pipeline(content_id, emit_event)` function signature
- Update the video stage to handle `"timed_out": True` from patient polling — set status to "captioned" (skip video) instead of "failed"

---

## Task 5: CRM Blueprints

**Files:**
- Create: `blueprints/public.py`, `blueprints/admin.py`, `blueprints/api.py`, `blueprints/products.py`, `blueprints/clients.py`, `blueprints/tasks.py`, `blueprints/email.py`
- Create: `chatbot.py`

- [ ] **Step 1: Copy CRM blueprints**

Copy these files from `CRM Demo For Claude Workshop/blueprints/` as-is:
- `public.py`, `api.py`, `products.py`, `clients.py`, `tasks.py`, `email.py`

- [ ] **Step 2: Copy and modify `blueprints/admin.py`**

Copy from CRM, then modify the dashboard route to also query content stats:
```python
# In dashboard():
from models import ContentItem
content_total = ContentItem.query.count()
content_ready = ContentItem.query.filter_by(status="ReadyToPost").count()
content_published = ContentItem.query.filter_by(status="published").count()
# Pass to template
```

- [ ] **Step 3: Copy `chatbot.py`**

Copy from `CRM Demo For Claude Workshop/chatbot.py` as-is.

---

## Task 6: Content Blueprint

**Files:**
- Create: `blueprints/content.py`, `blueprints/content_api.py`

- [ ] **Step 1: Create `blueprints/content.py`**

Content page routes (login required):
```python
from flask import Blueprint, render_template, Response, request
from auth import login_required
from models import ContentItem, PipelineLog
from extensions import db
import json, queue, threading

content_bp = Blueprint("content", __name__)

# Thread-safe SSE streams
active_streams = {}

@content_bp.route("/")
@login_required
def index():
    items = ContentItem.query.order_by(ContentItem.created_at.desc()).all()
    return render_template("content/index.html", items=items)

@content_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    item = ContentItem.query.get_or_404(item_id)
    logs = PipelineLog.query.filter_by(content_id=item_id).order_by(PipelineLog.created_at).all()
    return render_template("content/detail.html", item=item, logs=logs)
```

- [ ] **Step 2: Create `blueprints/content_api.py`**

Content API routes — create, run pipeline (SSE), publish:
```python
from flask import Blueprint, request, jsonify, Response, current_app
from auth import login_required
from models import ContentItem, PipelineLog
from extensions import db
from pipeline import run_pipeline
import json, queue, threading

content_api_bp = Blueprint("content_api", __name__)

@content_api_bp.route("/create", methods=["POST"])
@login_required
def create():
    data = request.get_json()
    item = ContentItem(
        input_text=data.get("input_text", ""),
        input_type=data.get("input_type", "idea"),
        platform=data.get("platform", "tiktok"),
        include_video=data.get("include_video", False),
        status="draft",
    )
    db.session.add(item)
    db.session.commit()

    # Run pipeline in background thread, stream SSE
    q = queue.Queue()

    def emit(stage, status, message, detail=""):
        q.put(json.dumps({"stage": stage, "status": status, "message": message, "detail": detail}))

    def run():
        with current_app.app_context():
            run_pipeline(item.id, emit)
        q.put("DONE")

    threading.Thread(target=run, daemon=True).start()

    def stream():
        while True:
            msg = q.get()
            if msg == "DONE":
                yield f"data: {json.dumps({'stage': 'done', 'status': 'complete'})}\n\n"
                break
            yield f"data: {msg}\n\n"

    return Response(stream(), mimetype="text/event-stream")

@content_api_bp.route("/<int:item_id>", methods=["GET"])
@login_required
def get_item(item_id):
    item = ContentItem.query.get_or_404(item_id)
    return jsonify(item.to_dict())

@content_api_bp.route("/<int:item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id):
    item = ContentItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True})

@content_api_bp.route("/<int:item_id>/publish", methods=["POST"])
@login_required
def publish(item_id):
    item = ContentItem.query.get_or_404(item_id)
    from services.getlate import publish_content
    result = publish_content(item)
    if result.get("demo"):
        item.status = "published"
    elif result.get("post_id"):
        item.status = "published"
    db.session.commit()
    return jsonify(result)
```

---

## Task 7: Help Blueprint & Interactive Page

**Files:**
- Create: `blueprints/help.py`, `templates/help/index.html`

- [ ] **Step 1: Create `blueprints/help.py`**

```python
from flask import Blueprint, render_template
from auth import login_required

help_bp = Blueprint("help", __name__)

@help_bp.route("/")
@login_required
def index():
    return render_template("help/index.html")
```

- [ ] **Step 2: Create `templates/help/index.html`**

Interactive walkthrough page with 5 Alpine.js expandable sections:

1. **System Overview** — HTML/CSS flow diagram (CRM + Content cycle)
2. **The CRM Side** — Contacts, deals, chatbot, products explained
3. **The Content Side** — 5-stage pipeline visual, API explanations
4. **API Keys & Services** — Checklist with required/optional, costs, demo mode
5. **Architecture** — Blueprints, models, SSE, feature toggles

Each section uses Alpine.js `x-show` with `x-collapse` transition. Each has "Try it" links. Use the dark gold design system.

---

## Task 8: Templates (Merged)

**Files:**
- Create: `templates/base.html`, `templates/base_admin.html`
- Create: all `templates/admin/*.html` (copy from CRM)
- Create: `templates/content/index.html`, `templates/content/create.html`, `templates/content/detail.html`
- Create: all `templates/public/*.html` (copy from CRM)

- [ ] **Step 1: Create `templates/base.html`**

Merge both apps' base templates. Use CRM's as the foundation (it has Tailwind, Alpine, toast system). Add Content Automation's CSS variables if any are missing.

- [ ] **Step 2: Create `templates/base_admin.html`**

Use CRM's sidebar layout but update navigation to include all 6 items:
```html
<!-- Sidebar nav -->
<nav class="sidebar-nav">
    <a href="/admin/dashboard" class="sidebar-link ...">Dashboard</a>
    <a href="/admin/contacts" class="sidebar-link ...">Contacts</a>
    <a href="/admin/deals" class="sidebar-link ...">Deals</a>
    <a href="/content" class="sidebar-link ...">Content</a>
    <a href="/admin/settings" class="sidebar-link ...">Settings</a>
    <a href="/help" class="sidebar-link ...">Help</a>
</nav>
```

Keep the chat toggle button and chat panel from CRM's base_admin.html.

- [ ] **Step 3: Copy all CRM admin templates**

Copy from `CRM Demo For Claude Workshop/templates/admin/` as-is. Modify `dashboard.html` to add a "Content" stats row.

- [ ] **Step 4: Copy all CRM public templates**

Copy from `CRM Demo For Claude Workshop/templates/public/` as-is.

- [ ] **Step 5: Create `templates/content/index.html`**

Port from Content Automation's `dashboard.html` — content list with status badges, filter tabs (All/Draft/Processing/Ready/Published), create button linking to `/content/create`.

- [ ] **Step 6: Create `templates/content/create.html`**

Port from Content Automation's `cam.html` (simplified):
- Input field (URL or text idea) with auto-detect
- Platform dropdown (TikTok, Instagram, YouTube, LinkedIn, Twitter)
- "Include Video" checkbox
- Generate button
- SSE log panel (X-ray view) showing pipeline events in real-time
- On completion: redirect to detail page

- [ ] **Step 7: Create `templates/content/detail.html`**

Port from Content Automation's `content_detail.html`:
- Left: script, image, video player, captions by platform, cost breakdown
- Right: pipeline journey timeline, log history
- Actions: Publish, Retry, Delete

---

## Task 9: Static Assets

**Files:**
- Create: `static/css/custom.css`, `static/js/chat.js`, `static/js/pipeline.js`

- [ ] **Step 1: Copy `static/css/custom.css`**

Copy from `CRM Demo For Claude Workshop/static/css/custom.css` — it's the complete dark gold design system. Add any content-specific styles (pipeline log, stage badges) at the end.

- [ ] **Step 2: Copy `static/js/chat.js`**

Copy from CRM as-is.

- [ ] **Step 3: Create `static/js/pipeline.js`**

Extract SSE handling logic from Content Automation's `cam.html` into a standalone JS file. Alpine.js component for pipeline visualization.

---

## Task 10: Seed Data

**Files:**
- Create: `seed.py`

- [ ] **Step 1: Create unified `seed.py`**

Merge CRM's seed.py (17 contacts, 8 deals, 4 products, etc.) with 5 demo content items at various statuses (draft, scripted, imageDone, ReadyToPost, published). Use SQLAlchemy for all inserts.

---

## Task 11: Settings Page Integration

**Files:**
- Modify: `blueprints/admin.py` — add settings route
- Create: `templates/admin/settings.html`

- [ ] **Step 1: Add settings route to admin blueprint**

Settings page that manages both CRM and content API keys:
- Business Name
- OpenRouter API Key (used by both chatbot + content)
- Kie.ai API Key (content)
- FireCrawl API Key (content)
- GetLate API Key (content)
- R2 Storage config (content)
- Stripe keys (CRM)
- Resend keys (CRM)

Save to Setting model. On save, also set `os.environ` for immediate pickup by services.

- [ ] **Step 2: Create `templates/admin/settings.html`**

Form with grouped sections (CRM Integrations / Content Integrations / Storage). Show connection status (green dot if key is set, grey if not). Match dark gold design system.

---

## Task 12: Tests

**Files:**
- Create: `tests/conftest.py`, `tests/test_auth.py`, `tests/test_content.py`, `tests/test_content_api.py`, `tests/test_help.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest
from app import create_app
from extensions import db as _db

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"})
    return client
```

- [ ] **Step 2: Create `tests/test_auth.py`**

Test login, logout, redirect when not authenticated.

- [ ] **Step 3: Create `tests/test_content.py`**

Test content index page loads, create page loads, detail page loads.

- [ ] **Step 4: Create `tests/test_content_api.py`**

Test create content item, get item, delete item. Test pipeline SSE endpoint returns event-stream.

- [ ] **Step 5: Create `tests/test_help.py`**

Test help page loads with all 5 sections present.

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```

---

## Task 13: Git Setup & Push

- [ ] **Step 1: Initialize git remote**

```bash
git remote add origin https://github.com/jjacuna/all-in-one-business-app.git
# or update if already set
git remote set-url origin https://github.com/jjacuna/all-in-one-business-app.git
```

- [ ] **Step 2: Commit and push**

```bash
git add .
git commit -m "feat: unified All-in-One Business App — CRM + Content Automation merged"
git push -u origin main
```

---

## Parallelization Guide

These tasks can run in parallel:
- **Wave 1:** Task 1 (scaffold) + Task 3 (services) + Task 9 (static assets)
- **Wave 2:** Task 2 (models) — needs extensions.py from Task 1
- **Wave 3:** Task 4 (pipeline) + Task 5 (CRM blueprints) + Task 7 (help) — need models
- **Wave 4:** Task 6 (content blueprint) + Task 8 (templates) + Task 10 (seed) + Task 11 (settings)
- **Wave 5:** Task 12 (tests) — needs everything
- **Wave 6:** Task 13 (git push) — needs tests passing
