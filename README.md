# All-in-One Business App v5.0

**A complete business operating system that replaces GoHighLevel, Calendly, Mailchimp, and Shopify — built with Flask, designed for small businesses, and ready to resell as a done-for-you service.**

Built by [Simple Tech Skills](https://simpletechskills.com) for the Saturday Workshop.

---

## 👋 New here? Start with this

If this is your first time looking at the project, read this 30-second tour before anything else.

**What you're looking at:** A complete small-business app — CRM, content automation, calendar, AI assistant, email, e-commerce — all running in one Python program (Flask) on your laptop. No SaaS subscriptions; you own everything.

**What you need:**
1. A Mac (or Linux/Windows) with Python 3.9 or later
2. ~10 minutes for the first setup
3. Optional: API keys from a few services (OpenAI, Cloudflare R2, etc.) if you want the AI / image / file-storage features to actually work. The app runs fine without them in "demo mode."

**Two ways to use this:**
- **As a business owner** — install it, customize it for your business, run your operations from one dashboard
- **As a reseller** — install it for clients, charge setup + monthly, replace their $300+/mo SaaS stack

Jump straight to **[Quick Start](#quick-start)** to get the app running.

---

## 🏗️ Architecture in plain English (the restaurant analogy)

If you've never built a web app before, this is the simplest way to picture what's happening when you run `python app.py`:

| Part of the app | Restaurant equivalent | What it does |
|---|---|---|
| **Flask** (`app.py`) | The restaurant building itself | Listens at the front door (a "port" — `8000`) and routes guests to the right room |
| **Blueprints** (`blueprints/`) | Individual rooms — dining room, bar, kitchen office | Group related pages together (CRM is one blueprint, Content is another) |
| **Templates** (`templates/`) | The dining room — what guests see | HTML pages styled with Tailwind CSS |
| **Models** (`models.py`) | The recipe book + ingredient labels | Defines the shape of every piece of data (Contact, Deal, ContentItem, etc.) |
| **Database** (SQLite / PostgreSQL) | The pantry | Where all your data actually lives |
| **Services** (`services/`) | Phone lines to suppliers | Calls to OpenRouter, Kie.ai, Resend, Stripe, etc. |
| **`.env` file** | The locked recipe book in the manager's office | Your API keys, never to be shared or committed |
| **`requirements.txt`** | The supplier shopping list | Tells `pip install` which Python packages to install |
| **Virtual environment** (`.venv/`) | A private kitchen for this restaurant only | Isolates this app's Python packages from anything else on your machine |
| **R2 (Cloudflare)** | The walk-in freezer | Permanent storage for big stuff (generated images, uploads) |
| **Server-Sent Events (SSE)** | The kitchen pass-through window | Real-time updates from kitchen (backend) to dining room (browser) during long-running tasks like AI image generation |

When a customer (your browser) places an order (clicks a link), it goes to the waiter (Flask routes), the waiter relays it to the kitchen (a blueprint function), the kitchen pulls ingredients from the pantry (the database) and maybe phones a supplier (calls an external service), and finally the waiter brings back the finished dish (an HTML page or JSON response).

---

## What Is This?

This is a single Flask application that gives any small business everything they need to run their operations from one login:

- **CRM** — contacts, deals pipeline, activity tracking
- **Content Automation** — AI-powered content creation with real-time pipeline visualization
- **Calendar Booking** — appointment scheduling with a public booking page
- **AI Assistant (Jackie)** — business advisor powered by OpenAI or OpenRouter
- **Email Marketing** — templates, automation, and send tracking via Resend
- **E-Commerce Store** — product catalog with Stripe checkout
- **Analytics Dashboard** — Umami-style visitor tracking and revenue charts
- **Website Pages** — landing pages, sales pages, and funnel management
- **Client Onboarding** — survey forms that auto-create CRM records

The goal: one app, one login, one subscription — replace $300+/month in SaaS tools.

---

## Who Is This For?

### Business Owners
Small business owners (gyms, salons, home services, professional services) who want to stop paying for GoHighLevel, Calendly, Mailchimp, and Shopify separately. Install this, customize it with Claude Code, and run your entire business from one dashboard.

### Resellers / Agency Owners
People who want to sell done-for-you business systems to local businesses. Use this as your template, customize it per client, and charge $2,000-$5,000 for setup + $97-$300/month for maintenance. The app includes a built-in sales playbook with pricing packages.

---

## Features

### CRM (Customer Relationship Management)
- **Contacts** — full contact database with name, email, phone, company, status (Lead/Customer/VIP/Inactive/Client/Archived), lead source tracking
- **Deals Pipeline** — list view with stage filtering (New Lead, Contacted, Proposal, Negotiation, Won, Lost), deal values, expected close dates
- **Activity Log** — automatic audit trail of all CRM actions
- **Client Notes** — rich notes attached to each contact record
- **Search & Filter** — search by name/email/company, filter by status

### Content Automation Engine
- **AI Content Creation** — generate social media posts from a URL or idea
- **6-Stage Pipeline** — Scrape (FireCrawl) → Script (OpenRouter LLM) → Image (Kie.ai Nano Banana Pro) → Video (Kie.ai Veo 3.1) → Caption (LLM) → Publish (Zernio)
- **Real-Time X-Ray** — watch the pipeline process in real-time via Server-Sent Events
- **Multi-Platform** — TikTok, Instagram, YouTube, LinkedIn, Facebook, Twitter, Threads, Pinterest
- **Platform-Specific Captions** — AI generates optimized captions per platform
- **Cost Tracking** — see exactly what each content piece costs to generate

### Calendar Booking
- **FullCalendar.js** — interactive monthly/weekly/list views
- **Drag-and-Drop** — reschedule appointments by dragging events
- **Public Booking Page** — shareable page at `/bookings/book` (no login required)
- **Availability Slots** — configure available time slots per day of week (30-min increments)
- **Auto-Contact Creation** — booking automatically creates a CRM contact
- **Status Management** — confirm, complete, or cancel bookings

### Jackie AI Assistant
- **Golden Orb UI** — animated pulsing orb with conversation below
- **Dual Provider** — works with OpenAI direct or OpenRouter (toggle via env var)
- **Business-Focused** — trained to help with marketing, operations, customer management, and growth strategy
- **Chat History** — persisted in localStorage, clear anytime
- **Demo Mode** — works without API keys (shows helpful setup message)

### Email Marketing
- **Email Templates** — create reusable templates with variable substitution ({{name}}, {{product_name}}, etc.)
- **Trigger-Based** — auto-send emails on purchase, signup, or custom triggers
- **Send Tracking** — log of all sent emails with status (sent/failed/mock)
- **Resend Integration** — production email delivery via Resend API
- **Demo Mode** — logs emails locally when no API key is set

### E-Commerce / Products
- **Product Catalog** — manage products with name, description, price, image, type (paid/free)
- **Active/Archived** — toggle products on/off the public store
- **Stripe Checkout** — integrated payment processing
- **Purchase Tracking** — all transactions linked to CRM contacts
- **Public Store** — customer-facing product page at `/products/store`

### Analytics Dashboard
- **Umami-Style Design** — KPI stats (views, visits, visitors, bounce rate, duration)
- **24-Hour Bar Chart** — visitor and pageview breakdown by hour (Chart.js)
- **Top Pages** — ranked list of most-visited pages with percentage bars
- **Top Referrers** — traffic source breakdown
- **Umami Cloud Integration** — optional real tracking via one script tag

### Stripe-Inspired Dashboard
- **Rolling 90-Day Revenue Chart** — gold line for current period, dashed ghost line for previous period comparison
- **KPI Cards** — total contacts, active leads, pipeline value, revenue won
- **Recent Transactions Feed** — Stripe-style scrolling list with paid/refunded/failed status badges
- **Content Engine Stats** — total items, ready to post, published

### Website Pages Manager
- **Page Inventory** — list of all website pages with paths and status
- **Funnel Visualization** — visual flow showing Landing Page → Sales Page → Thank You
- **Page Types** — funnel pages vs standalone pages
- **Quick Links** — open any page in a new tab directly from the manager

### Client Onboarding Survey
- **Public Survey Form** — shareable at `/onboarding/` (no login required)
- **7 Default Questions** — business name, industry, employee count, challenges, tools, budget, referral source
- **Configurable** — add/remove/reorder questions, support text/textarea/select types
- **CRM Integration** — submissions auto-create contacts and link survey answers
- **Admin View** — expandable list of all responses with Q&A pairs

### Help & Sales Playbook
- **How to Use This** (for business owners)
  - Quick start checklist (5 steps)
  - Feature overview cards for every module
  - Settings walkthrough for API keys
- **How to Sell This** (for resellers)
  - Three pricing packages: Starter ($2K + $97/mo), Professional ($3.5K + $197/mo), Enterprise ($5K + $297/mo)
  - Sales script outline
  - Client onboarding checklist
  - Upsell bolt-ons: Facebook Ads, SEO/AEO, Content Analytics, Advanced Automations
  - Links to coaching ($500/mo) and academy ($7/mo)

### Settings
- **API Key Management** — configure all service keys from the UI
- **Connection Indicators** — see which services are connected
- **Immediate Pickup** — keys saved in Settings are used by services instantly (no restart needed)
- **Feature Toggles** — enable/disable modules via environment variables

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask 3.x + SQLAlchemy ORM |
| **Frontend** | Tailwind CSS (CDN) + Alpine.js (CDN) |
| **Database** | SQLite (dev) / PostgreSQL (production via Railway) |
| **AI** | OpenRouter (Claude, GPT-4, Gemini) or OpenAI direct |
| **Images** | Kie.ai — Nano Banana Pro |
| **Video** | Kie.ai — Google Veo 3.1 |
| **Web Scraping** | FireCrawl |
| **Social Publishing** | Zernio (formerly GetLate.dev) — 15 platforms |
| **Email** | Resend |
| **Payments** | Stripe |
| **Storage** | Cloudflare R2 (S3-compatible, zero egress fees) |
| **Analytics** | Umami Cloud (optional) |
| **Calendar** | FullCalendar.js 6.x (CDN) |
| **Charts** | Chart.js (CDN) |
| **Testing** | pytest + Playwright (E2E) |
| **Deployment** | Railway + gunicorn |

---

## Quick Start

### One-Line Install (Mac)

```bash
curl -fsSL https://simpletechskills.com/setup.sh | bash
```

### One-Line Install (Windows — PowerShell as Admin)

```powershell
irm https://simpletechskills.com/setup.ps1 | iex
```

### Manual Setup

```bash
# Clone or download the project
cd "All-in-One-Business-App"

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional — app works in demo mode without them)

# Load demo data
python seed.py

# Start the app
python app.py
```

Open **http://localhost:8000** in your browser.

**Default local credentials** (change them in `.env` before deploying anywhere):
- Username: `admin`
- Password: `admin`

> ⚠️ **Never use `admin`/`admin` on a public deployment.** That's like leaving your back-office key under the welcome mat. The moment you push this to Railway or any cloud, change both `ADMIN_USER` and `ADMIN_PASS` in your environment variables to something strong, and rotate `SECRET_KEY` to a fresh random string.

---

## Project Structure

```
app.py                  # Flask factory — registers all blueprints, configures app
extensions.py           # Shared SQLAlchemy db instance
auth.py                 # login_required decorator + credential checking
models.py               # 18 SQLAlchemy models (CRM + Content + Bookings + Surveys)
chatbot.py              # CRM chatbot engine (OpenRouter-based)
pipeline.py             # 6-stage content automation pipeline
seed.py                 # Database seeder with demo data

blueprints/
  public.py             # Landing page, sales page, thank-you page
  admin.py              # Dashboard, contacts, deals, settings, pages, analytics
  api.py                # JSON API for CRM operations + chatbot
  content.py            # Content library UI
  content_api.py        # Content creation API + SSE streaming
  bookings.py           # Calendar booking system + public booking page
  jackie.py             # Jackie AI assistant chat interface
  onboarding.py         # Client onboarding survey
  products.py           # Product catalog + Stripe checkout
  clients.py            # Client management
  tasks.py              # Task tracker
  email.py              # Email campaigns + templates
  help.py               # Help & sales playbook

services/
  openai_chat.py        # Jackie AI — OpenAI/OpenRouter provider toggle
  openrouter.py         # Content LLM — script, caption, image prompt generation
  firecrawl.py          # Web scraping via FireCrawl API
  kie_ai.py             # Image (Nano Banana Pro) + Video (Veo 3.1) generation
  zernio.py             # Social media publishing via Zernio SDK
  r2_storage.py         # Cloudflare R2 file storage
  getlate.py            # Legacy social publishing (Zernio fallback)

templates/
  base.html             # Root HTML template (Tailwind, Alpine.js, Umami)
  base_admin.html       # Admin layout (sidebar, chat panel, branding)
  admin/                # Dashboard, contacts, deals, settings, bookings, analytics, etc.
  content/              # Content library, create form, detail view
  public/               # Landing page, store, booking form, onboarding survey
  help/                 # Help & sales playbook (two tabs)

static/
  css/custom.css        # Complete dark gold theme (3600+ lines)
  js/chat.js            # Alpine.js chat panel
  js/pipeline.js        # Alpine.js pipeline X-ray stream

tests/
  conftest.py           # pytest fixtures (unit + Playwright E2E)
  test_auth.py          # Authentication tests
  test_api.py           # API endpoint tests
  test_content.py       # Content page tests
  test_content_api.py   # Content API tests
  test_help.py          # Help page tests
  test_e2e.py           # 15 Playwright end-to-end tests

docs/
  ROADMAP.md            # Development roadmap with phases
  OPENAI_REALTIME_VOICE_SETUP.md    # Voice AI orb setup guide
  CLOUDFLARE_R2_SETUP.md            # R2 storage setup guide
  Zernio API Setup (1).md           # Social publishing setup guide

.env.example            # All environment variables with descriptions
requirements.txt        # Python dependencies
railway.toml            # Railway deployment config
Procfile                # gunicorn process declaration
CLAUDE.md               # Project instructions for Claude Code
```

---

## Database Models (18)

| Model | Table | Purpose |
|-------|-------|---------|
| Contact | contacts | Leads, customers, clients |
| Deal | deals | Sales pipeline |
| Note | notes | Quick contact notes |
| ActivityLog | activity_log | Audit trail |
| Product | products | Digital product catalog |
| Purchase | purchases | Transaction records |
| ClientNote | client_notes | Rich client documentation |
| Task | tasks | Internal task board |
| EmailTemplate | email_templates | Email automation templates |
| EmailLog | email_log | Sent email tracking |
| PageView | page_views | Page view analytics |
| ContentItem | content_items | Content pipeline items |
| PipelineLog | pipeline_logs | Pipeline event log |
| Setting | settings | Key/value config store |
| BookingSlot | booking_slots | Available appointment times |
| Booking | bookings | Confirmed appointments |
| SurveyQuestion | survey_questions | Configurable survey questions |
| SurveyResponse | survey_responses | Completed survey submissions |

---

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///app.db          # SQLite (dev) or PostgreSQL URL (prod)

# Auth
ADMIN_USER=instructor
ADMIN_PASS=SaturdayWorkshop2026!
SECRET_KEY=change-me-in-production

# Branding
BUSINESS_NAME=All-in-One Business App

# Feature Toggles (set to "false" to disable)
FEATURE_PRODUCTS=true
FEATURE_CLIENTS=true
FEATURE_TASKS=true
FEATURE_EMAIL=true
FEATURE_ANALYTICS=true
FEATURE_BOOKINGS=true

# Jackie AI
OPENAI_API_KEY=                        # For direct OpenAI
CHAT_PROVIDER=openrouter               # "openai" or "openrouter"
OPENAI_CHAT_MODEL=gpt-4o-mini

# Content Automation
OPENROUTER_API_KEY=                    # LLM for scripts, captions, chatbot
FIRECRAWL_API_KEY=                     # Web scraping
KIE_AI_API_KEY=                        # Image + video generation

# Social Publishing
ZERNIO_API_KEY=                        # Publish to 15 platforms

# Payments
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_CHECKOUT_URL=

# Email
RESEND_API_KEY=
RESEND_FROM_EMAIL=

# Storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_PUBLIC_URL=

# Analytics
UMAMI_WEBSITE_ID=
UMAMI_SCRIPT_URL=https://cloud.umami.is/script.js
```

**Demo mode:** The app works without any API keys. All services return placeholder data so students can explore every feature immediately.

---

## Testing

```bash
# Run unit tests (16 tests)
python -m pytest tests/test_auth.py tests/test_api.py tests/test_content.py tests/test_help.py -v

# Run Playwright E2E tests (15 tests)
pip install playwright pytest-playwright
playwright install chromium
python -m pytest tests/test_e2e.py -v

# Run E2E tests with visible browser (great for demos)
python -m pytest tests/test_e2e.py -v --headed --slowmo 500

# Run all tests
python -m pytest tests/ -v
```

**31 total tests, all passing** — covers authentication, API endpoints, content pages, help pages, and full E2E user flows (login, navigate all pages, submit onboarding form).

---

## Deploy to Railway

```bash
# Install Railway CLI
brew install railway          # Mac
# scoop install railway       # Windows

# Deploy
railway login
railway init -n "all-in-one-business-app"
railway add --database postgres
railway service               # select your app service
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}'
railway variables set SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
railway variables set ADMIN_USER="instructor"
railway variables set ADMIN_PASS="YourStrongPassword!"
railway up
railway domain                # get your public URL
```

---

## Sidebar Navigation

```
CRM
  Dashboard          — Stripe-inspired with revenue chart + transactions
  Contacts           — searchable contact database with status filters
  Deals              — sales pipeline list with stage filtering
  Pages              — website page manager with funnel visualization
  Products           — product catalog with active/archived toggle
  Analytics          — Umami-style visitor analytics

MARKETING
  Content            — AI content creation studio
  Email              — email templates and campaign management

TOOLS
  Bookings           — calendar scheduling with drag-and-drop
  Jackie AI          — AI business assistant with golden orb
  Manual & Help      — usage guide + sales playbook

SYSTEM
  Settings           — API keys and configuration
```

---

## Pricing Packages (For Resellers)

| Package | Setup Fee | Monthly | Includes |
|---------|-----------|---------|----------|
| **Starter** | $2,000 | $97/mo | Website + CRM + Calendar Booking |
| **Professional** | $3,500 | $197/mo | + Content Automation + Email Marketing |
| **Enterprise** | $5,000 | $297/mo | + AI Assistant + Analytics + Custom Development |

**Upsell Bolt-Ons:** Facebook Ads setup ($2,500), SEO/AEO optimization, Done-for-you content, Content analytics dashboard, Advanced email sequences

---

## API Costs (Per Usage)

| Service | Cost | What It Does |
|---------|------|-------------|
| OpenRouter (Gemini Flash) | ~$0.01/request | Scripts, captions, chatbot |
| Kie.ai (Nano Banana Pro) | ~$0.09/image | AI image generation |
| Kie.ai (Veo 3.1) | ~$0.30/video | AI video generation |
| FireCrawl | ~$0.01/scrape | Website content extraction |
| Zernio | Free (20 posts/mo) | Social media publishing |
| Resend | Free (3K emails/mo) | Transactional email |
| Cloudflare R2 | ~$0.015/GB/mo | File storage (zero egress) |
| Railway | ~$5-10/mo | Hosting + PostgreSQL |

**Total monthly cost for a small business:** ~$10-20/month in infrastructure, plus usage-based API costs.

---

## Branding

- **Powered by Dr.AI** — displayed in the sidebar footer
- **v5.0** — version number in footer
- **Simple Tech Skills** — coaching and academy links throughout
- **License** — resale license required for commercial redistribution

---

## Roadmap (Future)

- OpenAI Realtime Voice (golden orb with live voice conversations)
- Twilio SMS for booking confirmations
- Multi-tenant architecture (GoHighLevel-style sub-accounts)
- PWA wrapper for mobile app experience
- Google Workspace email (free 2K emails/day)
- Client document management with R2 storage
- Content analytics (pull Umami data via API)
- Stripe subscription billing for service tiers
- PDF export / print reports
- Team roles and permissions (admin/editor/viewer)
- White-label admin panel (custom logos, colors per tenant)
- Desktop app launcher (open without VS Code)

---

## Support

- **Coaching:** [simpletechskills.com/coaching](https://simpletechskills.com/coaching) — starts at $500/mo
- **Academy:** [simpletechskills.com/academy](https://simpletechskills.com/academy) — $7/mo community
- **Workshop:** Saturday Workshop — live coding sessions

---

*Built with Flask, powered by AI, designed for small business owners who want to own their tools.*
