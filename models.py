from datetime import datetime, date
from extensions import db


# ---------------------------------------------------------------------------
# CRM Models
# ---------------------------------------------------------------------------

class Contact(db.Model):
    __tablename__ = "contacts"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    email      = db.Column(db.String(200))
    phone      = db.Column(db.String(50))
    company    = db.Column(db.String(200))
    status     = db.Column(db.String(20), default="Lead")
    lead_source = db.Column(db.String(30), default="Other")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes       = db.relationship("Note",        backref="contact", lazy=True, cascade="all, delete-orphan")
    deals       = db.relationship("Deal",        backref="contact", lazy=True)
    activities  = db.relationship("ActivityLog", backref="contact", lazy=True)
    client_notes = db.relationship("ClientNote", backref="contact", lazy=True, cascade="all, delete-orphan")
    purchases   = db.relationship("Purchase",    backref="contact", lazy=True)
    email_logs  = db.relationship("EmailLog",    backref="contact", lazy=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "email":       self.email,
            "phone":       self.phone,
            "company":     self.company,
            "status":      self.status,
            "lead_source": self.lead_source,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
        }


class Deal(db.Model):
    __tablename__ = "deals"

    id                 = db.Column(db.Integer, primary_key=True)
    title              = db.Column(db.String(300), nullable=False)
    contact_id         = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    value              = db.Column(db.Numeric(12, 2), default=0)
    stage              = db.Column(db.String(30), default="New Lead")
    expected_close_date = db.Column(db.Date)
    won_lost_reason    = db.Column(db.Text)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    activities = db.relationship("ActivityLog", backref="deal", lazy=True)

    def to_dict(self):
        return {
            "id":                  self.id,
            "title":               self.title,
            "contact_id":          self.contact_id,
            "contact_name":        self.contact.name if self.contact else None,
            "value":               float(self.value) if self.value is not None else 0,
            "stage":               self.stage,
            "expected_close_date": self.expected_close_date.isoformat() if self.expected_close_date else None,
            "won_lost_reason":     self.won_lost_reason,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }


class Note(db.Model):
    __tablename__ = "notes"

    id         = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    content    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "contact_id": self.contact_id,
            "content":    self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id          = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    contact_id  = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id     = db.Column(db.Integer, db.ForeignKey("deals.id",    ondelete="SET NULL"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "action_type": self.action_type,
            "description": self.description,
            "contact_id":  self.contact_id,
            "deal_id":     self.deal_id,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }


class Product(db.Model):
    __tablename__ = "products"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text)
    price           = db.Column(db.Numeric(10, 2), default=0)
    product_type    = db.Column(db.String(20), default="paid")
    delivery_url    = db.Column(db.Text)
    stripe_price_id = db.Column(db.String(100))
    image_url       = db.Column(db.Text)
    active          = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":              self.id,
            "name":            self.name,
            "description":     self.description,
            "price":           float(self.price) if self.price is not None else 0,
            "product_type":    self.product_type,
            "delivery_url":    self.delivery_url,
            "stripe_price_id": self.stripe_price_id,
            "image_url":       self.image_url,
            "active":          self.active,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "updated_at":      self.updated_at.isoformat() if self.updated_at else None,
        }


class Purchase(db.Model):
    __tablename__ = "purchases"

    id                = db.Column(db.Integer, primary_key=True)
    contact_id        = db.Column(db.Integer, db.ForeignKey("contacts.id",  ondelete="SET NULL"), nullable=True)
    product_id        = db.Column(db.Integer, db.ForeignKey("products.id",  ondelete="SET NULL"), nullable=True)
    stripe_session_id = db.Column(db.String(200))
    amount            = db.Column(db.Numeric(10, 2))
    status            = db.Column(db.String(20), default="completed")
    purchased_at      = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", backref="purchases", lazy=True)

    def to_dict(self):
        return {
            "id":                self.id,
            "contact_id":        self.contact_id,
            "product_id":        self.product_id,
            "stripe_session_id": self.stripe_session_id,
            "amount":            float(self.amount) if self.amount is not None else None,
            "status":            self.status,
            "purchased_at":      self.purchased_at.isoformat() if self.purchased_at else None,
        }


class ClientNote(db.Model):
    __tablename__ = "client_notes"

    id         = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    title      = db.Column(db.String(300))
    content    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "contact_id": self.contact_id,
            "title":      self.title,
            "content":    self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Task(db.Model):
    __tablename__ = "tasks"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), default="todo")
    priority    = db.Column(db.String(10), default="medium")
    due_date    = db.Column(db.Date)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "title":       self.title,
            "description": self.description,
            "status":      self.status,
            "priority":    self.priority,
            "due_date":    self.due_date.isoformat() if self.due_date else None,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(200), nullable=False)
    subject      = db.Column(db.String(300))
    body_html    = db.Column(db.Text)
    trigger_type = db.Column(db.String(50))
    active       = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "subject":      self.subject,
            "body_html":    self.body_html,
            "trigger_type": self.trigger_type,
            "active":       self.active,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailLog(db.Model):
    __tablename__ = "email_log"

    id          = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    contact_id  = db.Column(db.Integer, db.ForeignKey("contacts.id",        ondelete="SET NULL"), nullable=True)
    to_email    = db.Column(db.String(200))
    subject     = db.Column(db.String(300))
    status      = db.Column(db.String(20), default="sent")
    sent_at     = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship("EmailTemplate", backref="email_logs", lazy=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "template_id": self.template_id,
            "contact_id":  self.contact_id,
            "to_email":    self.to_email,
            "subject":     self.subject,
            "status":      self.status,
            "sent_at":     self.sent_at.isoformat() if self.sent_at else None,
        }


class PageView(db.Model):
    __tablename__ = "page_views"

    id         = db.Column(db.Integer, primary_key=True)
    page       = db.Column(db.String(200))
    visitor_id = db.Column(db.String(100))
    referrer   = db.Column(db.String(500))
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "page":       self.page,
            "visitor_id": self.visitor_id,
            "referrer":   self.referrer,
            "contact_id": self.contact_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Content Models
# ---------------------------------------------------------------------------

class ContentItem(db.Model):
    __tablename__ = "content_items"

    id              = db.Column(db.Integer, primary_key=True)
    input_text      = db.Column(db.Text)
    input_type      = db.Column(db.String(10),  default="idea")
    platform        = db.Column(db.String(20),  default="tiktok")
    article_text    = db.Column(db.Text)
    article_title   = db.Column(db.String(500))
    word_count      = db.Column(db.Integer)
    script          = db.Column(db.Text)
    image_prompt    = db.Column(db.Text)
    image_url       = db.Column(db.Text)
    image_task_id   = db.Column(db.String(100))
    video_prompt    = db.Column(db.Text)
    video_url       = db.Column(db.Text)
    video_task_id   = db.Column(db.String(100))
    captions        = db.Column(db.Text)          # JSON string
    include_video   = db.Column(db.Boolean, default=False)
    status          = db.Column(db.String(30),  default="draft")
    cost_total      = db.Column(db.Float,       default=0.0)
    stage_durations = db.Column(db.Text)          # JSON string
    stage_costs     = db.Column(db.Text)          # JSON string
    r2_image_url    = db.Column(db.Text)
    r2_video_url    = db.Column(db.Text)
    scheduled_at    = db.Column(db.DateTime)
    published_at    = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pipeline_logs = db.relationship("PipelineLog", backref="content_item", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":              self.id,
            "input_text":      self.input_text,
            "input_type":      self.input_type,
            "platform":        self.platform,
            "article_text":    self.article_text,
            "article_title":   self.article_title,
            "word_count":      self.word_count,
            "script":          self.script,
            "image_prompt":    self.image_prompt,
            "image_url":       self.image_url,
            "image_task_id":   self.image_task_id,
            "video_prompt":    self.video_prompt,
            "video_url":       self.video_url,
            "video_task_id":   self.video_task_id,
            "captions":        self.captions,
            "include_video":   self.include_video,
            "status":          self.status,
            "cost_total":      self.cost_total,
            "stage_durations": self.stage_durations,
            "stage_costs":     self.stage_costs,
            "r2_image_url":    self.r2_image_url,
            "r2_video_url":    self.r2_video_url,
            "scheduled_at":    self.scheduled_at.isoformat() if self.scheduled_at else None,
            "published_at":    self.published_at.isoformat() if self.published_at else None,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "updated_at":      self.updated_at.isoformat() if self.updated_at else None,
        }


class PipelineLog(db.Model):
    __tablename__ = "pipeline_logs"

    id         = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    stage      = db.Column(db.String(30))
    status     = db.Column(db.String(20))
    message    = db.Column(db.Text)
    detail     = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "content_id": self.content_id,
            "stage":      self.stage,
            "status":     self.status,
            "message":    self.message,
            "detail":     self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Booking Models
# ---------------------------------------------------------------------------

class BookingSlot(db.Model):
    """Available time slots configured by the business owner."""
    __tablename__ = "booking_slots"

    id          = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time  = db.Column(db.String(5), nullable=False)  # "09:00"
    end_time    = db.Column(db.String(5), nullable=False)  # "10:00"
    slot_type   = db.Column(db.String(50), default="consultation")
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    """A confirmed appointment."""
    __tablename__ = "bookings"

    id           = db.Column(db.Integer, primary_key=True)
    contact_id   = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    client_name  = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(30), default="")
    date         = db.Column(db.Date, nullable=False)
    start_time   = db.Column(db.String(5), nullable=False)
    end_time     = db.Column(db.String(5), nullable=False)
    slot_type    = db.Column(db.String(50), default="consultation")
    status       = db.Column(db.String(20), default="confirmed")  # confirmed/cancelled/completed
    notes        = db.Column(db.Text, default="")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    contact = db.relationship("Contact", backref="bookings")

    def to_dict(self):
        return {
            "id": self.id, "contact_id": self.contact_id,
            "client_name": self.client_name, "client_email": self.client_email,
            "client_phone": self.client_phone,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time, "end_time": self.end_time,
            "slot_type": self.slot_type, "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Survey / Onboarding Models
# ---------------------------------------------------------------------------

class SurveyQuestion(db.Model):
    """Configurable survey questions."""
    __tablename__ = "survey_questions"

    id            = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), default="text")  # text/select/textarea
    options       = db.Column(db.Text, default="")  # comma-separated for select
    sort_order    = db.Column(db.Integer, default=0)
    active        = db.Column(db.Boolean, default=True)


class SurveyResponse(db.Model):
    """A completed survey submission."""
    __tablename__ = "survey_responses"

    id               = db.Column(db.Integer, primary_key=True)
    contact_id       = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    respondent_name  = db.Column(db.String(100), nullable=False)
    respondent_email = db.Column(db.String(120), nullable=False)
    answers          = db.Column(db.Text, default="{}")  # JSON dict
    submitted_at     = db.Column(db.DateTime, default=datetime.utcnow)

    contact = db.relationship("Contact", backref="survey_responses")

    def to_dict(self):
        return {
            "id": self.id, "contact_id": self.contact_id,
            "respondent_name": self.respondent_name,
            "respondent_email": self.respondent_email,
            "answers": self.answers,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Setting(db.Model):
    __tablename__ = "settings"

    key   = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        row = Setting.query.get(key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = Setting.query.get(key)
        if row:
            row.value = value
        else:
            row = Setting(key=key, value=value)
            db.session.add(row)
        db.session.commit()


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------

def log_activity(action_type, description, contact_id=None, deal_id=None):
    activity = ActivityLog(
        action_type=action_type,
        description=description,
        contact_id=contact_id,
        deal_id=deal_id,
    )
    db.session.add(activity)
    return activity
