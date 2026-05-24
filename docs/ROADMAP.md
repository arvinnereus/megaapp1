# All-in-One Business App — Roadmap

**Last Updated:** 2026-05-05
**Repo:** https://github.com/jjacuna/all-in-one-business-app.git
**Status:** Phase 1 Complete, Phase 2 Ready

---

## What Was Built (Phase 1 — COMPLETE)

### Session: 2026-05-04

Merged the CRM Demo and Content Automation Demo into a single Flask app. Everything lives at the repo root — the two original subdirectories remain as reference only.

**Architecture:**
- Single Flask app with blueprint pattern
- 14 SQLAlchemy models (11 CRM + 3 Content) in one `models.py`
- One login, one `.env`, one database (SQLite dev / PostgreSQL prod)
- Left sidebar navigation: Dashboard, Contacts, Deals, Content, Settings, Help

**Files created (60 total):**
```
app.py, extensions.py, auth.py, models.py, chatbot.py, pipeline.py, seed.py
blueprints/  (10 files: public, admin, api, content, content_api, products, clients, tasks, email, help)
services/    (5 files: openrouter, kie_ai, firecrawl, getlate, r2_storage)
templates/   (16 files: base, base_admin, 5 admin, 3 content, 1 help, 6 public)
static/      (3 files: custom.css, chat.js, pipeline.js)
tests/       (7 files: conftest + 5 test modules)
config:      .env.example, Procfile, railway.toml, CLAUDE.md, .gitignore
docs:        design spec, implementation plan, this roadmap
```

**Key features working:**
- CRM: contacts, deals pipeline, AI chatbot, products/store, clients, tasks, email automation
- Content: create from URL or idea, platform dropdown, SSE X-ray pipeline visualization
- Patient Kie.ai polling (5s/3min for images, 30s-60s/15min for video, graceful timeout)
- Interactive Help page with 5 expandable sections
- Settings page for all API keys with connection indicators
- Demo mode (everything works without API keys)
- 19/19 tests passing

**Commit:** `978b79f` pushed to `origin/main`

---

## Phase 2: Polish & Workshop Prep (NEXT SESSION)

Priority items to make the app workshop-ready.

### 2.1 — Smoke Test the Full Flow
- [ ] Run `python seed.py` and verify all demo data loads
- [ ] Start app, log in, verify Dashboard shows both CRM + Content stats
- [ ] Navigate every sidebar link — confirm all pages render
- [ ] Create a content item (idea mode, no API keys) — verify demo mode works
- [ ] Create a content item with real API keys — verify full pipeline runs
- [ ] Test the AI chatbot (with OpenRouter key)
- [ ] Verify Settings page saves keys and services pick them up immediately

### 2.2 — UI/UX Fixes
- [ ] Verify dark gold theme is consistent across ALL pages (CRM + Content + Help)
- [ ] Check mobile responsiveness on sidebar collapse
- [ ] Fix any Alpine.js scope conflicts between chat panel and page-level x-data
- [ ] Ensure toast notifications work on all pages
- [ ] Add loading spinners where needed (content generation, deal moves)

### 2.3 — Content Detail Page Polish
- [ ] Verify script display, image preview, video player all render correctly
- [ ] Verify pipeline timeline shows correct stage indicators
- [ ] Test "Publish Now" button (demo mode + live mode)
- [ ] Add "Repurpose for..." button (re-runs script + caption for different platform)
- [ ] Add "Retry" button for failed items (re-runs pipeline from failed stage)

### 2.4 — Dashboard Unification
- [ ] Add content items to the activity timeline on Dashboard
- [ ] Add a "Recent Content" section showing last 5 items with quick links
- [ ] Add content conversion funnel if analytics enabled (items created → published)

---

## Phase 3: Workshop Experience Enhancements

### 3.1 — Onboarding Flow
- [ ] First-time login wizard: walks students through setting up API keys
- [ ] Step-by-step checklist on Dashboard: "Set up OpenRouter" → "Create first contact" → "Generate first content"
- [ ] Progress indicator showing how many setup steps are complete

### 3.2 — Help Page Improvements
- [ ] Add GIF/animation of the pipeline running (screen recording embedded)
- [ ] Add "Glossary" section explaining terms (SSE, API, Blueprint, ORM, etc.)
- [ ] Add "Common Errors" troubleshooting section
- [ ] Add cost calculator: "If I generate X posts/week, it costs ~$Y/month"

### 3.3 — Content Templates
- [ ] Pre-built content templates: "Motivational Quote", "How-To Tip", "Behind the Scenes"
- [ ] Template selector on create page
- [ ] Each template pre-fills the idea text + suggested platform

### 3.4 — Batch Content Generation
- [ ] Queue mode: add multiple ideas, generate them one-by-one automatically
- [ ] Batch status view showing progress across all queued items
- [ ] Estimated time remaining based on average generation time

---

## Phase 4: CRM-Content Integration

### 4.1 — Link Content to Contacts
- [ ] When content is published, auto-log an ActivityLog entry
- [ ] On Contact detail, show "Content created for this lead" section
- [ ] Content attribution: track which content brought in which leads

### 4.2 — Auto Lead Capture from Content
- [ ] When a lead magnet is downloaded, auto-create Contact + Deal
- [ ] Tag contacts with the content/campaign that captured them
- [ ] Dashboard shows "Leads from Content" metric

### 4.3 — Email + Content Triggers
- [ ] Auto-email new leads a welcome sequence
- [ ] Auto-generate follow-up content for stale leads
- [ ] Content publish triggers: notify via email when new content goes live

---

## Phase 5: Deployment & Production

### 5.1 — Railway Deployment
- [ ] Deploy to Railway with PostgreSQL
- [ ] Set all environment variables
- [ ] Run seed.py in production for demo data
- [ ] Configure custom domain (if applicable)
- [ ] Set up health check monitoring

### 5.2 — Security Hardening
- [ ] Move from env-var auth to hashed passwords (bcrypt)
- [ ] Add rate limiting on login and API endpoints
- [ ] Add CSRF protection on forms
- [ ] Encrypt API keys at rest in the Settings table
- [ ] Add session timeout (auto-logout after inactivity)

### 5.3 — Performance
- [ ] Add database indexes on frequently queried columns (status, created_at, contact_id)
- [ ] Add pagination to contacts list and content list
- [ ] Lazy-load pipeline logs on content detail page
- [ ] Cache dashboard stats (refresh every 60s, not every page load)

---

## Phase 6: Advanced Features (Future)

### 6.1 — Multi-Platform Publishing
- [ ] Publish to multiple platforms simultaneously from one content item
- [ ] Platform-specific preview cards showing how the post will look
- [ ] GetLate.dev scheduling integration (pick date/time per platform)

### 6.2 — Content Analytics
- [ ] Track published content performance (views, engagement) via platform APIs
- [ ] ROI dashboard: cost per post vs. leads generated
- [ ] Best-performing content type analysis

### 6.3 — AI Improvements
- [ ] Smart content suggestions based on CRM data ("Your leads in X industry respond to Y topics")
- [ ] Auto-generate deals follow-up emails from chatbot
- [ ] Content repurposing: auto-adapt one post to all platforms with one click

### 6.4 — Multi-User Support
- [ ] User registration + roles (admin, editor, viewer)
- [ ] Team workspace with shared contacts and content
- [ ] Audit log showing who did what

---

## Technical Debt & Known Issues

### Known Issues
- SQLAlchemy deprecation warnings for `datetime.utcnow()` — cosmetic, no impact
- `Query.get()` legacy API warnings — cosmetic, no impact
- Chat panel Alpine.js scope conflict may occur on some pages (needs testing)
- Feature blueprints (products, clients, tasks, email) were copied from CRM — may need template path adjustments if any hardcoded paths exist

### Tech Debt
- [ ] Replace `datetime.utcnow()` with `datetime.now(UTC)` throughout models.py
- [ ] Replace `Query.get()` with `db.session.get()` in all blueprints
- [ ] Add type hints to all model methods
- [ ] Extract inline JavaScript from templates into separate .js files
- [ ] Add Playwright end-to-end tests for full user flows

---

## Architecture Reference

### Models (14)
| Model | Table | Purpose |
|-------|-------|---------|
| Contact | contacts | Leads, customers, clients |
| Deal | deals | Sales pipeline |
| Note | notes | Quick contact notes |
| ActivityLog | activity_log | Audit trail |
| Product | products | Digital products catalog |
| Purchase | purchases | Transaction records |
| ClientNote | client_notes | Rich markdown notes |
| Task | tasks | Internal task board |
| EmailTemplate | email_templates | Email automation |
| EmailLog | email_log | Sent email tracking |
| PageView | page_views | Analytics |
| ContentItem | content_items | Content pipeline items |
| PipelineLog | pipeline_logs | Pipeline event log |
| Setting | settings | Key/value config store |

### Blueprints (10)
| Blueprint | Prefix | Auth | Feature Toggle |
|-----------|--------|------|----------------|
| public | / | No | Always on |
| admin | /admin | Yes | Always on |
| api | /api | Yes | Always on |
| content | /content | Yes | Always on |
| content_api | /content/api | Yes | Always on |
| help | /help | Yes | Always on |
| products | (mixed) | Yes | FEATURE_PRODUCTS |
| clients | (mixed) | Yes | FEATURE_CLIENTS |
| tasks | (mixed) | Yes | FEATURE_TASKS |
| email | (mixed) | Yes | FEATURE_EMAIL |

### Services (5)
| Service | API | Cost | Demo Mode |
|---------|-----|------|-----------|
| OpenRouter | LLM (scripts, captions, chatbot) | ~$0.01/req | Placeholder text |
| Kie.ai | Images (Nano Banana) + Video (Veo 3.1) | $0.09 img / $0.19 vid | Placeholder URLs |
| FireCrawl | URL scraping | ~$0.01/scrape | Sample article |
| GetLate.dev | Social media publishing | Free tier | Simulated publish |
| R2 Storage | Permanent file hosting | ~$0.015/GB/mo | Passthrough URLs |

### Content Pipeline Stages
```
Input (URL/idea) → Scrape (FireCrawl) → Script (OpenRouter) → Image (Kie.ai) → Video (Kie.ai, optional) → Caption (OpenRouter) → Ready to Post → Publish (GetLate)
```

### Patient Polling (Kie.ai)
```
Image:  Poll every 5s,  max 3 minutes
Video:  Phase 1 — every 30s for 5 min
        Phase 2 — every 60s for 10 more min (15 min total)
        On timeout: graceful return, don't crash pipeline
```

### Environment Variables
```
Required:  SECRET_KEY, DATABASE_URL, ADMIN_USER, ADMIN_PASS
Branding:  BUSINESS_NAME
Toggles:   FEATURE_PRODUCTS, FEATURE_CLIENTS, FEATURE_TASKS, FEATURE_EMAIL, FEATURE_ANALYTICS
Content:   OPENROUTER_API_KEY, FIRECRAWL_API_KEY, KIE_AI_API_KEY, GETLATE_API_KEY
CRM:       STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL, LEAD_MAGNET_URL
Storage:   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL
```

### Quick Start
```bash
cd "All-in-One Business App - Saturday Workshop"
pip install -r requirements.txt
cp .env.example .env          # Edit with your keys
python seed.py                # Load demo data
python app.py                 # http://localhost:8000
# Login: admin / changeme
```

### Test
```bash
python -m pytest tests/ -v    # 19 tests
```

### Deploy (Railway)
```bash
# Push to GitHub, connect repo in Railway, add PostgreSQL, set env vars
# Auto-deploys via Procfile
```
