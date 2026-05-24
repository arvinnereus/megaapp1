# All-in-One Business App — Design Spec

**Date:** 2026-05-04
**Status:** Approved
**Approach:** Blueprint Merge (Approach A)

## Overview

Combine the CRM Demo and Content Automation Demo into a single Flask application. One codebase, one database, one login, one `.env` file. The app teaches workshop students how a real business system works while being genuinely useful for business owners.

**Name:** All-in-One Business App
**Repo:** https://github.com/jjacuna/all-in-one-business-app.git

## Architecture

Single Flask app using the blueprint pattern. Content Automation is ported from raw SQLite to SQLAlchemy and added as new blueprints alongside the existing CRM blueprints.

### Project Structure

```
all-in-one-business-app/
├── app.py                    # Flask factory, config, blueprint registration
├── models.py                 # All models (CRM + Content) under SQLAlchemy
├── auth.py                   # Single login decorator
├── extensions.py             # db = SQLAlchemy()
├── chatbot.py                # AI chatbot (OpenRouter)
├── pipeline.py               # Content pipeline orchestrator (SSE)
├── seed.py                   # Demo data for both CRM + Content
│
├── blueprints/
│   ├── public.py             # Landing page, store, lead capture
│   ├── admin.py              # Dashboard, contacts, deals, login
│   ├── api.py                # JSON API (CRM endpoints)
│   ├── content.py            # Content creation, detail, pipeline trigger
│   ├── content_api.py        # Content JSON API (create, run, poll, publish)
│   ├── products.py           # Products + Stripe
│   ├── clients.py            # Client management
│   ├── tasks.py              # Internal task kanban
│   ├── email.py              # Email templates + Resend
│   └── help.py               # Interactive help/manual page
│
├── services/
│   ├── openrouter.py         # LLM for scripts, captions, image prompts
│   ├── kie_ai.py             # Image + video generation (patient polling)
│   ├── firecrawl.py          # URL → markdown scraping
│   ├── getlate.py            # Social media publishing
│   └── r2_storage.py         # Cloudflare R2 file storage
│
├── templates/
│   ├── base.html             # Root layout (Tailwind + Alpine CDN)
│   ├── base_admin.html       # Admin layout with left sidebar nav
│   ├── admin/                # CRM pages
│   ├── content/              # Content pages (index, create, detail)
│   ├── help/                 # Interactive help (index)
│   └── public/               # Landing, store, thank you
│
├── static/
│   ├── css/custom.css        # Dark gold design system
│   └── js/
│       ├── chat.js           # AI chatbot component
│       └── pipeline.js       # SSE pipeline visualization
│
├── tests/
├── .env.example
├── requirements.txt
├── Procfile
└── railway.toml
```

### Left Sidebar Navigation

1. Dashboard (combined CRM + content KPIs)
2. Contacts
3. Deals
4. Content
5. Settings
6. Help

## Data Model

### Existing CRM Models (keep as-is)

Contact, Deal, Note, ActivityLog, Product, Purchase, ClientNote, Task, EmailTemplate, EmailLog, PageView — all existing SQLAlchemy models, no changes.

### New Content Models (ported to SQLAlchemy)

**ContentItem**
- id, input_text, input_type ('url'/'idea')
- platform ('tiktok'/'instagram'/'youtube'/'linkedin'/'twitter')
- article_text, article_title, word_count (from FireCrawl)
- script (from OpenRouter)
- image_prompt, image_url, image_task_id (from Kie.ai)
- video_prompt, video_url, video_task_id (from Kie.ai)
- captions (from OpenRouter)
- include_video (Boolean)
- status: draft → processed → scripted → imageDone → videoDone → captioned → ReadyToPost → published → failed
- cost_total (Float), stage_durations (JSON), stage_costs (JSON)
- scheduled_at, published_at, created_at, updated_at

**PipelineLog**
- id, content_id (FK → ContentItem), stage, status ('progress'/'error'/'polling'/'success'), message, detail, created_at

**Setting**
- key (PK), value — key/value store for API keys and app settings

## Content Pipeline

Sequential, one item at a time, SSE streaming for X-ray visualization.

### Stages

1. **scrape** — FireCrawl URL → markdown (skip if input_type='idea')
2. **script** — OpenRouter generates platform-specific script
3. **image** — Kie.ai Nano Banana Pro generates image
4. **video** — Kie.ai Veo 3.1 Fast generates one 8s video (optional)
5. **caption** — OpenRouter generates platform-specific caption
6. **publish** — Manual trigger via GetLate.dev

### Platform Selection

- Dropdown on create form: TikTok, Instagram, YouTube, LinkedIn, Twitter
- Script and caption tailored to platform style/character limits
- After generation: "Repurpose for..." button re-runs script + caption for other platforms

### Patient Polling (Kie.ai Fix)

**Image polling:**
- Poll every 5 seconds, up to 3 minutes max
- Each poll emits SSE event for X-ray display
- On timeout: mark failed, log error, pipeline continues

**Video polling:**
- Poll every 30 seconds for first 5 minutes
- Then every 60 seconds for up to 10 more minutes (15 min total)
- Each poll emits SSE event
- On timeout: stop waiting, mark failed with clear message
- Don't cancel the Kie.ai task — it may still finish

### Demo Mode

All services return educational placeholder responses when API keys are missing. App is fully functional without any API keys for workshop demos.

## Interactive Help Page

Single-page visual walkthrough built with Alpine.js expandable sections.

### Sections

1. **System Overview** — HTML/CSS flow diagram showing CRM + Content cycle
2. **The CRM Side** — Contacts, deals pipeline, AI chatbot, products/store
3. **The Content Side** — 5-stage pipeline diagram, what each API does, X-ray explanation
4. **API Keys & Services** — Interactive checklist: required vs optional, demo vs live mode, costs, signup links
5. **Architecture for Developers** — Flask blueprints, models, SSE streaming, feature toggles

Each section has "Try it" links to the actual features.

## Environment Variables

Single `.env` file:

```env
# Required
SECRET_KEY=
DATABASE_URL=sqlite:///app.db
ADMIN_USER=admin
ADMIN_PASS=changeme
BUSINESS_NAME=My Business

# CRM Feature Toggles
FEATURE_PRODUCTS=true
FEATURE_CLIENTS=true
FEATURE_TASKS=true
FEATURE_EMAIL=true
FEATURE_ANALYTICS=true

# Content Automation (all optional, demo mode if unset)
OPENROUTER_API_KEY=
FIRECRAWL_API_KEY=
KIE_AI_API_KEY=
GETLATE_API_KEY=

# Optional Integrations
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
RESEND_API_KEY=
RESEND_FROM_EMAIL=
LEAD_MAGNET_URL=

# Optional Storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=
```

## Unified Dashboard

Combined KPIs showing both CRM and content stats:
- **CRM:** Total contacts, leads, pipeline value, revenue, won deals
- **Content:** Total items, items by status, recent pipeline runs, content created this week

## Tech Stack

- Flask 3.x, SQLAlchemy 2.x, Gunicorn
- Tailwind CSS 3.x (CDN), Alpine.js 3.x (CDN)
- SQLite (dev) / PostgreSQL (prod via Railway)
- OpenRouter, FireCrawl, Kie.ai, GetLate.dev, Stripe, Resend
- pytest + Playwright for testing

## Deployment

Railway with PostgreSQL. Single Procfile, single `railway.toml`.
