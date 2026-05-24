"""
blueprints/content.py — Content Blueprint
==========================================
Page routes for the Content Library section.
Registered at url_prefix="/content".

Teaching notes:
- Blueprint pattern: group related routes into their own module
- login_required decorator: enforces authentication on every route
- SQLAlchemy ORM: ContentItem.query replaces raw SQL
"""

from flask import Blueprint, render_template
from auth import login_required
from models import ContentItem, PipelineLog

content_bp = Blueprint("content", __name__)


@content_bp.route("/")
@login_required
def index():
    """Content library - list all content items."""
    items = ContentItem.query.order_by(ContentItem.created_at.desc()).all()
    return render_template("content/index.html", items=items)


@content_bp.route("/create")
@login_required
def create():
    """Create new content item form."""
    import os
    from models import Setting
    headshot_url = Setting.get("HEADSHOT_URL", "")

    # Pre-flight: check which API keys are configured
    api_status = {
        "ai": bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")),
        "scraper": bool(os.environ.get("FIRECRAWL_API_KEY")),
        "image": bool(os.environ.get("KIE_AI_API_KEY") or os.environ.get("KIE_API_KEY")),
    }
    api_status["ready"] = api_status["ai"]  # AI is the minimum requirement

    return render_template("content/create.html", headshot_url=headshot_url, api_status=api_status)


@content_bp.route("/<int:item_id>")
@login_required
def detail(item_id):
    """Content detail with pipeline X-ray view."""
    import json as _json
    item = ContentItem.query.get_or_404(item_id)
    logs = PipelineLog.query.filter_by(content_id=item_id).order_by(PipelineLog.created_at).all()

    # Parse captions JSON for template
    captions_parsed = {}
    if item.captions:
        try:
            captions_parsed = _json.loads(item.captions)
        except (ValueError, TypeError):
            pass
    item.captions_parsed = captions_parsed

    # Build stage info from stage_durations / stage_costs JSON
    pipeline_stages = ["scrape", "script", "image", "video", "caption"]
    stage_durations = {}
    stage_costs = {}
    if item.stage_durations:
        try:
            stage_durations = _json.loads(item.stage_durations)
        except (ValueError, TypeError):
            pass
    if item.stage_costs:
        try:
            stage_costs = _json.loads(item.stage_costs)
        except (ValueError, TypeError):
            pass

    stage_info = []
    completed_stages = set()
    error_stages = set()
    skipped_stages = set()

    for s in pipeline_stages:
        info = {"name": s, "duration": stage_durations.get(s), "cost": stage_costs.get(s)}
        stage_info.append(info)

    # Determine stage statuses from logs
    for log in logs:
        stage = (log.stage or "").lower()
        if log.status == "complete":
            completed_stages.add(stage)
        elif log.status == "error":
            error_stages.add(stage)

    # If input_type is 'idea', scrape is skipped
    if item.input_type == "idea":
        skipped_stages.add("scrape")
    if not item.include_video:
        skipped_stages.add("video")

    return render_template(
        "content/detail.html",
        item=item, logs=[l.to_dict() for l in logs],
        stage_info=stage_info,
        completed_stages=completed_stages,
        error_stages=error_stages,
        skipped_stages=skipped_stages,
    )
