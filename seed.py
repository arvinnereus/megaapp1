"""Seed the database with demo data for the All-in-One Business App.
Run: python seed.py
"""
from extensions import db
from models import (
    Contact, Deal, Note, ActivityLog,
    Product, Purchase, ClientNote, Task,
    EmailTemplate, EmailLog, PageView,
    ContentItem, PipelineLog, Setting,
    BookingSlot, Booking, SurveyQuestion, SurveyResponse,
)
from datetime import datetime, timedelta
import random
import uuid
import json


def run_seed(drop_tables=False):
    """Seed demo data. Called from app.py auto-seed or standalone."""
    if drop_tables:
        print("Dropping all tables...")
        db.drop_all()
        print("Recreating all tables...")
        db.create_all()

    # =================================================================
    # CRM DEMO DATA
    # =================================================================

    # --- CONTACTS (17) ---
    print("Seeding contacts...")
    contacts_data = [
        {"name": "Maria Garcia", "email": "maria.garcia@email.com", "phone": "(555) 234-5678", "company": "Garcia Properties", "status": "Client", "lead_source": "Referral"},
        {"name": "James Wilson", "email": "james.w@outlook.com", "phone": "(555) 345-6789", "company": "Wilson Financial", "status": "Lead", "lead_source": "Website Form"},
        {"name": "Sarah Chen", "email": "sarah.chen@gmail.com", "phone": "(555) 456-7890", "company": "Chen & Associates", "status": "VIP", "lead_source": "Workshop"},
        {"name": "Michael Brown", "email": "mbrown@brownrealty.com", "phone": "(555) 567-8901", "company": "Brown Realty Group", "status": "Customer", "lead_source": "Referral"},
        {"name": "Jessica Taylor", "email": "jtaylor@email.com", "phone": "(555) 678-9012", "company": "", "status": "Lead", "lead_source": "TikTok"},
        {"name": "Robert Martinez", "email": "rmartinez@gmail.com", "phone": "(555) 789-0123", "company": "Martinez Ventures", "status": "Lead", "lead_source": "Cold Outreach"},
        {"name": "Amanda Johnson", "email": "amanda.j@hotmail.com", "phone": "(555) 890-1234", "company": "Johnson Consulting", "status": "Customer", "lead_source": "Cold Outreach"},
        {"name": "David Kim", "email": "dkim@kimgroup.com", "phone": "(555) 901-2345", "company": "Kim Investment Group", "status": "Client", "lead_source": "Referral"},
        {"name": "Lisa Patel", "email": "lpatel@email.com", "phone": "(555) 012-3456", "company": "Patel & Partners", "status": "Lead", "lead_source": "Website Form"},
        {"name": "Chris Anderson", "email": "chris.a@gmail.com", "phone": "(555) 123-4567", "company": "", "status": "Lead", "lead_source": "TikTok"},
        {"name": "Nicole Thompson", "email": "nthompson@thompsonlaw.com", "phone": "(555) 234-5679", "company": "Thompson Law Firm", "status": "Customer", "lead_source": "Workshop"},
        {"name": "Daniel Lee", "email": "dlee@email.com", "phone": "(555) 345-6780", "company": "Lee Capital", "status": "Inactive", "lead_source": "Cold Outreach"},
        {"name": "Rachel White", "email": "rwhite@gmail.com", "phone": "(555) 456-7891", "company": "", "status": "Lead", "lead_source": "Website Form"},
        {"name": "Kevin Harris", "email": "kharris@harrisgroup.com", "phone": "(555) 567-8902", "company": "Harris Group LLC", "status": "Lead", "lead_source": "Cold Outreach"},
        {"name": "Sophia Rivera", "email": "srivera@email.com", "phone": "(555) 678-9013", "company": "Rivera Homes", "status": "Client", "lead_source": "Referral"},
        {"name": "Marcus Wright", "email": "mwright@email.com", "phone": "(555) 789-0124", "company": "Wright Coaching", "status": "Client", "lead_source": "Workshop"},
        {"name": "Emily Foster", "email": "efoster@foster.co", "phone": "(555) 890-1235", "company": "Foster Digital", "status": "Archived", "lead_source": "Referral"},
    ]

    contacts = []
    for c in contacts_data:
        contact = Contact(**c, created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)))
        db.session.add(contact)
        contacts.append(contact)
    db.session.flush()
    print(f"  {len(contacts)} contacts created")

    # --- DEALS (8) ---
    print("Seeding deals...")
    deals_data = [
        {"title": "Garcia Properties - Home Purchase", "contact": 0, "value": 450000, "stage": "Won"},
        {"title": "Wilson Financial - Refinance", "contact": 1, "value": 325000, "stage": "New Lead"},
        {"title": "Chen & Associates - Commercial Loan", "contact": 2, "value": 1200000, "stage": "Negotiation"},
        {"title": "Brown Realty - Investment Property", "contact": 3, "value": 675000, "stage": "Proposal"},
        {"title": "Taylor - First-Time Buyer", "contact": 4, "value": 285000, "stage": "Contacted"},
        {"title": "Martinez Ventures - Portfolio Loan", "contact": 5, "value": 2500000, "stage": "New Lead"},
        {"title": "Kim Investment - Multi-Unit Purchase", "contact": 7, "value": 3400000, "stage": "Won"},
        {"title": "Patel & Partners - Office Mortgage", "contact": 8, "value": 890000, "stage": "Lost"},
    ]

    deals = []
    for d in deals_data:
        deal = Deal(
            title=d["title"], contact_id=contacts[d["contact"]].id,
            value=d["value"], stage=d["stage"],
            expected_close_date=datetime.utcnow().date() + timedelta(days=random.randint(7, 90)),
            won_lost_reason="Client found better rate elsewhere" if d["stage"] == "Lost" else None,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
        )
        db.session.add(deal)
        deals.append(deal)
    db.session.flush()
    print(f"  {len(deals)} deals created")

    # --- NOTES (22) ---
    print("Seeding notes...")
    notes_data = [
        (0, "Initial consultation went well. Maria is looking to purchase a 3-bedroom home in the suburbs. Budget around $450K."),
        (0, "Pre-approval completed. Maria qualified for $475K. Sending property listings tomorrow."),
        (0, "Closed! Maria purchased the property at 123 Oak Street. Great referral potential."),
        (1, "James called about refinancing his current home. Currently at 6.5% - could save him $400/month."),
        (1, "Sent refinance comparison sheet. James is reviewing with his wife."),
        (2, "Sarah needs a commercial loan for her new office space. Looking at $1.2M. She's been a great client -- treating this as VIP."),
        (2, "Sent term sheet. Sarah is reviewing with her business partner. Follow up Friday."),
        (3, "Michael referred by Maria Garcia. Looking for an investment property -- rental income focused."),
        (3, "Showed Michael 3 properties. He's interested in the duplex on Elm Street."),
        (3, "Michael submitted offer on duplex. Waiting for seller response."),
        (4, "Jessica found us on TikTok. First-time buyer, needs education on the process. Scheduled intro call."),
        (5, "Cold outreach via LinkedIn. Robert has a portfolio of 5 properties, looking to add more."),
        (5, "Robert interested in portfolio loan. Scheduling a detailed consultation next week."),
        (7, "David is a high-net-worth client. Looking at multi-unit investment. Needs specialized lending."),
        (7, "Met with David's financial advisor. They want to structure this as an LLC purchase."),
        (7, "David approved! Closing on a 12-unit apartment complex. Huge deal."),
        (8, "Lisa needs office space mortgage for her accounting firm. Straightforward deal."),
        (8, "Lisa's application submitted. Awaiting underwriting."),
        (10, "Nicole referred by Sarah Chen. Looking at buying her first commercial property for her law firm."),
        (11, "Daniel went cold after initial call. Sent 2 follow-ups, no response. Moving to inactive."),
        (14, "Sophia closed on her new home! She's already referring friends."),
        (14, "Sophia sent over two referrals -- following up with both this week."),
    ]

    for contact_idx, content in notes_data:
        note = Note(contact_id=contacts[contact_idx].id, content=content, created_at=datetime.utcnow() - timedelta(days=random.randint(1, 45)))
        db.session.add(note)
    print(f"  {len(notes_data)} notes created")

    # --- ACTIVITY LOG (32) ---
    print("Seeding activity log...")
    activities = [
        ("contact_created", "Created contact: Maria Garcia", 0, None),
        ("contact_created", "Created contact: James Wilson", 1, None),
        ("contact_created", "Created contact: Sarah Chen", 2, None),
        ("contact_created", "Created contact: Michael Brown", 3, None),
        ("contact_created", "Created contact: Jessica Taylor", 4, None),
        ("contact_created", "Created contact: Robert Martinez", 5, None),
        ("contact_created", "Created contact: Amanda Johnson", 6, None),
        ("contact_created", "Created contact: David Kim", 7, None),
        ("deal_created", "Created deal: Garcia Properties - Home Purchase", 0, 0),
        ("deal_created", "Created deal: Wilson Financial - Refinance", 1, 1),
        ("deal_created", "Created deal: Chen & Associates - Commercial Loan", 2, 2),
        ("deal_created", "Created deal: Brown Realty - Investment Property", 3, 3),
        ("deal_created", "Created deal: Taylor - First-Time Buyer", 4, 4),
        ("deal_created", "Created deal: Martinez Ventures - Portfolio Loan", 5, 5),
        ("deal_created", "Created deal: Kim Investment - Multi-Unit Purchase", 7, 6),
        ("deal_created", "Created deal: Patel & Partners - Office Mortgage", 8, 7),
        ("deal_moved", "Moved 'Garcia Properties' from Proposal to Won", 0, 0),
        ("deal_moved", "Moved 'Chen & Associates' from Proposal to Negotiation", 2, 2),
        ("deal_moved", "Moved 'Brown Realty' from Contacted to Proposal", 3, 3),
        ("deal_moved", "Moved 'Taylor' from New Lead to Contacted", 4, 4),
        ("deal_moved", "Moved 'Kim Investment' from Negotiation to Won", 7, 6),
        ("deal_moved", "Moved 'Patel & Partners' from Proposal to Lost", 8, 7),
        ("note_added", "Added note to Maria Garcia", 0, None),
        ("note_added", "Added note to James Wilson", 1, None),
        ("note_added", "Added note to Sarah Chen", 2, None),
        ("note_added", "Added note to Michael Brown", 3, None),
        ("note_added", "Added note to David Kim", 7, None),
        ("note_added", "Added note to Sophia Rivera", 14, None),
        ("contact_updated", "Updated Daniel Lee status to Inactive", 11, None),
        ("contact_updated", "Updated Sarah Chen status to VIP", 2, None),
        ("contact_updated", "Updated Amanda Johnson status to Customer", 6, None),
        ("contact_created", "New lead from landing page: Lisa Patel", 8, None),
    ]

    for action_type, desc, contact_idx, deal_idx in activities:
        activity = ActivityLog(
            action_type=action_type, description=desc,
            contact_id=contacts[contact_idx].id,
            deal_id=deals[deal_idx].id if deal_idx is not None else None,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23)),
        )
        db.session.add(activity)
    print(f"  {len(activities)} activity log entries created")

    # --- PRODUCTS (4) ---
    print("Seeding products...")
    products_data = [
        {
            "name": "Business Blueprint PDF",
            "description": "A comprehensive 50-page guide to building your coaching business from scratch. Covers branding, pricing, client acquisition, and scaling strategies.",
            "price": 47,
            "product_type": "paid",
            "delivery_url": "https://example.com/downloads/business-blueprint.pdf",
            "image_url": "",
            "active": True,
        },
        {
            "name": "Video Workshop: Client Acquisition Mastery",
            "description": "3-hour recorded workshop covering proven strategies to attract and convert high-ticket clients. Includes templates and scripts.",
            "price": 197,
            "product_type": "paid",
            "delivery_url": "https://example.com/workshop/client-acquisition",
            "image_url": "",
            "active": True,
        },
        {
            "name": "Free Checklist: 10 Steps to Your First Client",
            "description": "A quick-start checklist for new coaches and consultants. Perfect lead magnet to grow your email list.",
            "price": 0,
            "product_type": "free",
            "delivery_url": "https://example.com/downloads/first-client-checklist.pdf",
            "image_url": "",
            "active": True,
        },
        {
            "name": "VIP Coaching Toolkit",
            "description": "Premium bundle with templates, scripts, SOPs, and video training. Everything you need to run a 6-figure coaching business.",
            "price": 497,
            "product_type": "paid",
            "delivery_url": "https://example.com/downloads/vip-toolkit",
            "image_url": "",
            "active": True,
        },
    ]

    products = []
    for p in products_data:
        product = Product(**p, created_at=datetime.utcnow() - timedelta(days=random.randint(10, 60)))
        db.session.add(product)
        products.append(product)
    db.session.flush()
    print(f"  {len(products)} products created")

    # --- PURCHASES (10) ---
    print("Seeding purchases...")
    purchases_data = [
        {"contact": 0, "product": 0, "amount": 47, "status": "completed", "days_ago": 25},
        {"contact": 0, "product": 1, "amount": 197, "status": "completed", "days_ago": 12},
        {"contact": 2, "product": 3, "amount": 497, "status": "completed", "days_ago": 8},
        {"contact": 3, "product": 0, "amount": 47, "status": "completed", "days_ago": 20},
        {"contact": 6, "product": 1, "amount": 197, "status": "completed", "days_ago": 15},
        {"contact": 7, "product": 3, "amount": 497, "status": "completed", "days_ago": 5},
        {"contact": 7, "product": 0, "amount": 47, "status": "completed", "days_ago": 30},
        {"contact": 10, "product": 2, "amount": 0, "status": "completed", "days_ago": 18},
        {"contact": 14, "product": 0, "amount": 47, "status": "completed", "days_ago": 10},
        {"contact": 15, "product": 1, "amount": 197, "status": "completed", "days_ago": 3},
    ]

    for p in purchases_data:
        purchase = Purchase(
            contact_id=contacts[p["contact"]].id,
            product_id=products[p["product"]].id,
            stripe_session_id=f"mock_cs_{uuid.uuid4().hex[:16]}",
            amount=p["amount"],
            status=p["status"],
            purchased_at=datetime.utcnow() - timedelta(days=p["days_ago"]),
        )
        db.session.add(purchase)
    print(f"  {len(purchases_data)} purchases created")

    # --- CLIENT NOTES (6) ---
    print("Seeding client notes...")
    client_notes_data = [
        {"contact": 0, "title": "Onboarding Call Notes", "content": "**Key Takeaways:**\n\n- Maria wants to focus on growing her rental portfolio\n- Budget: $500K-$750K per property\n- Timeline: 2 properties by end of year\n- Preferred communication: Email + monthly calls\n\n**Action Items:**\n- Send market analysis for target neighborhoods\n- Schedule follow-up in 2 weeks"},
        {"contact": 0, "title": "Q1 Review", "content": "Maria closed on her first investment property. Very happy with the process.\n\n**Results:**\n- Property purchased: 123 Oak Street\n- Purchase price: $450,000\n- Expected monthly rent: $2,800\n\n**Next Steps:**\n- Start looking at second property\n- Review financing options for LLC structure"},
        {"contact": 7, "title": "VIP Client Setup", "content": "David Kim is a high-net-worth investor. His portfolio:\n\n- 12-unit apartment complex (just closed)\n- 3 commercial properties\n- Looking to expand into multi-family\n\n**Special Considerations:**\n- Works with financial advisor (copy them on emails)\n- Prefers LLC structure for all purchases\n- Quick decision-maker, values speed"},
        {"contact": 7, "title": "Investment Strategy Meeting", "content": "Met with David and his advisor to discuss 2024 strategy.\n\n**Goals:**\n- Acquire 2-3 more multi-family units\n- Total portfolio value target: $10M\n- Focus on B+ neighborhoods with appreciation potential\n\n**Notes:**\n- David prefers off-market deals\n- Willing to pay premium for turnkey properties"},
        {"contact": 14, "title": "Welcome Package Sent", "content": "Sent Sophia the welcome package including:\n\n- Client onboarding guide\n- Communication preferences form\n- Calendar link for monthly check-ins\n\nSophia mentioned she has 2 referrals coming our way."},
        {"contact": 15, "title": "Initial Consultation", "content": "Marcus runs a coaching business and needs help with:\n\n- **Branding:** Wants to refresh his online presence\n- **Funnel:** Needs a lead magnet + email sequence\n- **Product:** Considering launching a group coaching program\n\nRecommended the VIP Coaching Toolkit as a starting point."},
    ]

    for cn in client_notes_data:
        client_note = ClientNote(
            contact_id=contacts[cn["contact"]].id,
            title=cn["title"],
            content=cn["content"],
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
        )
        db.session.add(client_note)
    print(f"  {len(client_notes_data)} client notes created")

    # --- TASKS (8) ---
    print("Seeding tasks...")
    tasks_data = [
        {"title": "Follow up with James Wilson on refinance", "description": "James was reviewing the comparison sheet with his wife. Call to check in.", "status": "todo", "priority": "high", "due_days": 2},
        {"title": "Send property listings to Maria", "description": "Maria is looking for her second investment property. Pull comps for target neighborhoods.", "status": "todo", "priority": "medium", "due_days": 5},
        {"title": "Prepare proposal for Chen & Associates", "description": "Commercial loan proposal for Sarah's new office space. $1.2M deal.", "status": "in_progress", "priority": "high", "due_days": 3},
        {"title": "Update CRM with new lead sources", "description": "Add tracking for Instagram and YouTube lead sources.", "status": "todo", "priority": "low", "due_days": 14},
        {"title": "Schedule team meeting for Q2 planning", "description": "Review pipeline, set targets, discuss marketing strategy.", "status": "todo", "priority": "medium", "due_days": 7},
        {"title": "Close deal with Brown Realty", "description": "Michael's offer on the duplex is pending. Follow up with seller's agent.", "status": "in_progress", "priority": "high", "due_days": 1},
        {"title": "Create email template for new clients", "description": "Draft a welcome email template for new client onboarding.", "status": "done", "priority": "medium", "due_days": -3},
        {"title": "Review and update pricing page", "description": "Update the sales page with new testimonials and pricing.", "status": "done", "priority": "low", "due_days": -7},
    ]

    for t in tasks_data:
        task = Task(
            title=t["title"],
            description=t["description"],
            status=t["status"],
            priority=t["priority"],
            due_date=datetime.utcnow().date() + timedelta(days=t["due_days"]),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
        )
        db.session.add(task)
    print(f"  {len(tasks_data)} tasks created")

    # --- EMAIL TEMPLATES (2) ---
    print("Seeding email templates...")
    email_templates_data = [
        {
            "name": "Lead Magnet Delivery",
            "subject": "Here's your free guide, {{name}}!",
            "body_html": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #C7A35A;">Welcome, {{name}}!</h2>
    <p>Thank you for signing up. Here's the free resource you requested:</p>
    <p style="text-align: center; margin: 30px 0;">
    <a href="{{lead_magnet_url}}" style="background: #C7A35A; color: #0B0B0D; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold;">Download Your Free Guide</a>
    </p>
    <p>If you have any questions, just reply to this email.</p>
    <p style="color: #666; font-size: 14px;">Best regards,<br>The Team</p>
</div>""",
            "trigger_type": "lead_magnet",
            "active": True,
        },
        {
            "name": "Purchase Confirmation",
            "subject": "Your purchase of {{product_name}} is confirmed!",
            "body_html": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #C7A35A;">Thank you for your purchase, {{name}}!</h2>
    <p>Your order for <strong>{{product_name}}</strong> ({{price}}) has been confirmed.</p>
    <p style="text-align: center; margin: 30px 0;">
    <a href="{{delivery_url}}" style="background: #C7A35A; color: #0B0B0D; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold;">Access Your Purchase</a>
    </p>
    <p>If you have any questions about your purchase, just reply to this email.</p>
    <p style="color: #666; font-size: 14px;">Best regards,<br>The Team</p>
</div>""",
            "trigger_type": "purchase_confirmation",
            "active": True,
        },
    ]

    templates = []
    for et in email_templates_data:
        template = EmailTemplate(**et, created_at=datetime.utcnow() - timedelta(days=30))
        db.session.add(template)
        templates.append(template)
    db.session.flush()
    print(f"  {len(email_templates_data)} email templates created")

    # --- EMAIL LOG (6 mock entries) ---
    print("Seeding email logs...")
    email_log_data = [
        {"template": 0, "contact": 1, "subject": "Here's your free guide, James!", "status": "mock", "days_ago": 20},
        {"template": 0, "contact": 4, "subject": "Here's your free guide, Jessica!", "status": "mock", "days_ago": 18},
        {"template": 0, "contact": 8, "subject": "Here's your free guide, Lisa!", "status": "mock", "days_ago": 15},
        {"template": 1, "contact": 0, "subject": "Your purchase of Business Blueprint PDF is confirmed!", "status": "mock", "days_ago": 25},
        {"template": 1, "contact": 2, "subject": "Your purchase of VIP Coaching Toolkit is confirmed!", "status": "mock", "days_ago": 8},
        {"template": 1, "contact": 7, "subject": "Your purchase of VIP Coaching Toolkit is confirmed!", "status": "mock", "days_ago": 5},
    ]

    for el in email_log_data:
        log = EmailLog(
            template_id=templates[el["template"]].id,
            contact_id=contacts[el["contact"]].id,
            to_email=contacts[el["contact"]].email,
            subject=el["subject"],
            status=el["status"],
            sent_at=datetime.utcnow() - timedelta(days=el["days_ago"]),
        )
        db.session.add(log)
    print(f"  {len(email_log_data)} email log entries created")

    # --- PAGE VIEWS (250 random) ---
    print("Seeding page views...")
    pages = ["/lp", "/sales", "/store"]
    for _ in range(250):
        page_view = PageView(
            page=random.choice(pages),
            visitor_id=str(uuid.uuid4()),
            referrer=random.choice([None, "https://google.com", "https://tiktok.com", "https://instagram.com", "direct"]),
            created_at=datetime.utcnow() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            ),
        )
        db.session.add(page_view)
    print("  250 page views created")

    # =================================================================
    # CONTENT AUTOMATION DEMO DATA
    # =================================================================
    print("Seeding content items...")

    # 1. Published content (complete)
    content_published = ContentItem(
        input_text="5 ways AI can automate your small business marketing",
        input_type="idea",
        platform="tiktok",
        script="Hook: Are you still doing marketing manually? Here are 5 ways AI can do it for you...\n\n1. Automated social media scheduling\n2. AI-generated captions and hashtags\n3. Smart content repurposing\n4. Automated email sequences\n5. AI-powered ad targeting\n\nCTA: Follow for more AI business tips!",
        image_prompt="A futuristic robot helping a small business owner at a desk with holographic marketing dashboards floating around them, cinematic lighting, dark gold color scheme",
        image_url="https://placehold.co/1080x1920/0B0B0D/C7A35A?text=AI+Marketing+Tips",
        video_prompt="A dynamic montage of AI-powered marketing tools in action",
        video_url="https://placehold.co/1080x1920/0B0B0D/C7A35A?text=Video+Preview",
        captions=json.dumps({
            "tiktok": "5 ways AI can automate your marketing. #AImarketing #SmallBusiness #Automation #TikTokTips",
            "instagram": "Stop doing marketing manually. Let AI handle these 5 tasks for you. Save this for later!",
            "youtube": "5 Ways AI Can Automate Your Small Business Marketing (You're Wasting Time Without These)",
        }),
        include_video=True,
        status="published",
        cost_total=0.15,
        published_at=datetime.utcnow() - timedelta(days=3),
        created_at=datetime.utcnow() - timedelta(days=5),
    )
    db.session.add(content_published)

    # 2. ReadyToPost content (image done, no video)
    content_ready = ContentItem(
        input_text="How to build a CRM in one weekend with Claude Code",
        input_type="idea",
        platform="youtube",
        script="Intro: What if I told you that you could build a fully functional CRM this weekend?\n\nI'm going to show you exactly how I built a complete CRM with contacts, deals, email automation, and an AI chatbot -- all using Claude Code.\n\nStep 1: Set up your Flask project structure\nStep 2: Define your data models\nStep 3: Build the admin dashboard\nStep 4: Add the AI chatbot\nStep 5: Deploy to Railway\n\nOutro: If you want the full walkthrough, check the link in my bio.",
        image_prompt="A split-screen showing code on one side and a beautiful dark-themed CRM dashboard on the other, with golden accent highlights",
        image_url="https://placehold.co/1920x1080/0B0B0D/C7A35A?text=Build+a+CRM",
        captions=json.dumps({
            "youtube": "How to Build a CRM in One Weekend with Claude Code | Full Tutorial",
            "tiktok": "I built an entire CRM in one weekend. Here's how. #ClaudeCode #VibeCoding #CRM #SaaS",
        }),
        include_video=False,
        status="ReadyToPost",
        cost_total=0.08,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    db.session.add(content_ready)

    # 3. Scripted content (in progress)
    content_scripted = ContentItem(
        input_text="https://example.com/blog/ai-content-creation-guide",
        input_type="url",
        platform="instagram",
        article_text="A comprehensive guide to using AI for content creation...",
        article_title="The Ultimate Guide to AI Content Creation",
        word_count=2500,
        script="Hook: Creating content used to take me 8 hours a day. Now it takes 30 minutes.\n\nHere's the exact system I use:\n\n1. Feed my ideas into an AI pipeline\n2. Generate scripts automatically\n3. Create images with AI\n4. Auto-generate captions for every platform\n5. Schedule and publish\n\nThe result? 10x more content in 1/10th the time.\n\nCTA: Drop 'SYSTEM' in the comments and I'll send you the full breakdown.",
        include_video=False,
        status="scripted",
        cost_total=0.04,
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    db.session.add(content_scripted)

    # 4. Draft content (just created)
    content_draft = ContentItem(
        input_text="The future of no-code tools for solopreneurs",
        input_type="idea",
        platform="tiktok",
        include_video=False,
        status="draft",
        cost_total=0.0,
        created_at=datetime.utcnow() - timedelta(hours=6),
    )
    db.session.add(content_draft)

    # 5. Failed content
    content_failed = ContentItem(
        input_text="https://expired-domain.example.com/article-that-doesnt-exist",
        input_type="url",
        platform="tiktok",
        include_video=False,
        status="failed",
        cost_total=0.0,
        created_at=datetime.utcnow() - timedelta(days=4),
    )
    db.session.add(content_failed)

    db.session.flush()
    print("  5 content items created (published, ReadyToPost, scripted, draft, failed)")

    # --- PIPELINE LOGS ---
    print("Seeding pipeline logs...")
    pipeline_logs = [
        # Logs for published content
        {"content_id": content_published.id, "stage": "scrape", "status": "success", "message": "Input processed as idea", "days_ago": 5},
        {"content_id": content_published.id, "stage": "script", "status": "success", "message": "Script generated (245 words)", "days_ago": 5},
        {"content_id": content_published.id, "stage": "image", "status": "success", "message": "Image generated successfully", "days_ago": 5},
        {"content_id": content_published.id, "stage": "video", "status": "success", "message": "Video generated successfully", "days_ago": 4},
        {"content_id": content_published.id, "stage": "captions", "status": "success", "message": "Captions generated for 3 platforms", "days_ago": 4},
        {"content_id": content_published.id, "stage": "done", "status": "success", "message": "Pipeline complete -- ready to post", "days_ago": 4},
        # Logs for ready content
        {"content_id": content_ready.id, "stage": "scrape", "status": "success", "message": "Input processed as idea", "days_ago": 2},
        {"content_id": content_ready.id, "stage": "script", "status": "success", "message": "Script generated (310 words)", "days_ago": 2},
        {"content_id": content_ready.id, "stage": "image", "status": "success", "message": "Image generated successfully", "days_ago": 2},
        {"content_id": content_ready.id, "stage": "captions", "status": "success", "message": "Captions generated for 2 platforms", "days_ago": 2},
        {"content_id": content_ready.id, "stage": "done", "status": "success", "message": "Pipeline complete -- ready to post", "days_ago": 2},
        # Logs for failed content
        {"content_id": content_failed.id, "stage": "scrape", "status": "error", "message": "Failed to fetch URL: 404 Not Found", "days_ago": 4},
    ]

    for pl in pipeline_logs:
        log = PipelineLog(
            content_id=pl["content_id"],
            stage=pl["stage"],
            status=pl["status"],
            message=pl["message"],
            created_at=datetime.utcnow() - timedelta(days=pl["days_ago"], hours=random.randint(0, 12)),
        )
        db.session.add(log)
    print(f"  {len(pipeline_logs)} pipeline log entries created")

    # =================================================================
    # DEFAULT SETTINGS
    # =================================================================
    print("Seeding default settings...")
    Setting.set("BUSINESS_NAME", "All-in-One Business App")
    print("  Business name set")

    db.session.commit()

    # =================================================================
    # BOOKING SLOTS & BOOKINGS
    # =================================================================
    print("Seeding booking slots...")
    booking_slots = []
    for day in range(5):  # Mon-Fri
        for hour in range(9, 17):  # 9am-4pm
            slot = BookingSlot(
                day_of_week=day,
                start_time=f"{hour:02d}:00",
                end_time=f"{hour+1:02d}:00",
                slot_type="consultation" if hour < 12 else "follow-up",
            )
            db.session.add(slot)
            booking_slots.append(slot)
    db.session.flush()

    print("Seeding bookings...")
    from datetime import date as dt_date
    today = dt_date.today()
    bookings_data = [
        Booking(contact_id=contacts[0].id, client_name=contacts[0].name, client_email=contacts[0].email or "demo@example.com",
                date=today + timedelta(days=2), start_time="10:00", end_time="11:00", slot_type="consultation", status="confirmed", notes="Initial consultation"),
        Booking(contact_id=contacts[1].id, client_name=contacts[1].name, client_email=contacts[1].email or "demo2@example.com",
                date=today + timedelta(days=3), start_time="14:00", end_time="15:00", slot_type="follow-up", status="confirmed", notes="Follow up on proposal"),
        Booking(contact_id=contacts[2].id, client_name=contacts[2].name, client_email=contacts[2].email or "demo3@example.com",
                date=today - timedelta(days=5), start_time="09:00", end_time="10:00", slot_type="consultation", status="completed", notes="Completed onboarding"),
    ]
    for b in bookings_data:
        db.session.add(b)

    # =================================================================
    # SURVEY QUESTIONS & RESPONSES
    # =================================================================
    print("Seeding survey questions...")
    survey_questions = [
        SurveyQuestion(question_text="What is your business name?", question_type="text", sort_order=1),
        SurveyQuestion(question_text="What industry are you in?", question_type="select",
                      options="Fitness/Gym,Restaurant/Food,Retail,Home Services,Professional Services,Health/Wellness,Real Estate,Other", sort_order=2),
        SurveyQuestion(question_text="How many employees do you have?", question_type="select",
                      options="Just me,2-5,6-10,11-25,26+", sort_order=3),
        SurveyQuestion(question_text="What is your biggest challenge right now?", question_type="textarea", sort_order=4),
        SurveyQuestion(question_text="What tools/software are you currently using?", question_type="textarea", sort_order=5),
        SurveyQuestion(question_text="What is your monthly marketing budget?", question_type="select",
                      options="Under $500,$500-$1000,$1000-$2500,$2500-$5000,$5000+", sort_order=6),
        SurveyQuestion(question_text="How did you hear about us?", question_type="select",
                      options="Facebook,Instagram,Google,Referral,Workshop,Other", sort_order=7),
    ]
    for q in survey_questions:
        db.session.add(q)
    db.session.flush()

    print("Seeding survey responses...")
    survey_responses = [
        SurveyResponse(
            contact_id=contacts[0].id, respondent_name=contacts[0].name,
            respondent_email=contacts[0].email or "demo@example.com",
            answers=json.dumps({"1": "Peak Fitness Gym", "2": "Fitness/Gym", "3": "6-10",
                               "4": "Inconsistent marketing and no online presence",
                               "5": "GoDaddy website, Excel spreadsheets, pen and paper",
                               "6": "Under $500", "7": "Referral"}),
        ),
        SurveyResponse(
            contact_id=contacts[3].id, respondent_name=contacts[3].name,
            respondent_email=contacts[3].email or "demo4@example.com",
            answers=json.dumps({"1": "Bright Smiles Dental", "2": "Health/Wellness", "3": "11-25",
                               "4": "Need better patient follow-up and appointment reminders",
                               "5": "Go High Level, Calendly, Mailchimp",
                               "6": "$1000-$2500", "7": "Workshop"}),
        ),
    ]
    for sr in survey_responses:
        db.session.add(sr)

    db.session.commit()

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)
    print(f"  Contacts:        {len(contacts)}")
    print(f"  Deals:           {len(deals)}")
    print(f"  Notes:           {len(notes_data)}")
    print(f"  Activities:      {len(activities)}")
    print(f"  Products:        {len(products)}")
    print(f"  Purchases:       {len(purchases_data)}")
    print(f"  Client Notes:    {len(client_notes_data)}")
    print(f"  Tasks:           {len(tasks_data)}")
    print(f"  Email Templates: {len(email_templates_data)}")
    print(f"  Email Logs:      {len(email_log_data)}")
    print(f"  Page Views:      250")
    print(f"  Content Items:   5")
    print(f"  Pipeline Logs:   {len(pipeline_logs)}")
    print(f"  Settings:        1")
    print("=" * 60)


if __name__ == "__main__":
    from app import app
    with app.app_context():
        run_seed(drop_tables=True)
