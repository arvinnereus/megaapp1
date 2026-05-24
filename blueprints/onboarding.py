"""Client onboarding survey — public form + admin view."""
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from auth import login_required
from extensions import db
from models import SurveyQuestion, SurveyResponse, Contact, log_activity

onboarding_bp = Blueprint("onboarding", __name__)


@onboarding_bp.route("/")
def public_form():
    """Public survey form — no auth required."""
    questions = SurveyQuestion.query.filter_by(active=True).order_by(SurveyQuestion.sort_order).all()
    return render_template("public/onboarding.html", questions=questions)


@onboarding_bp.route("/submit", methods=["POST"])
def submit():
    """Submit survey — creates/links Contact and saves answers."""
    data = request.form
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    if not name or not email:
        return redirect(url_for("onboarding.public_form"))

    # Find or create contact
    contact = Contact.query.filter_by(email=email).first()
    if not contact:
        contact = Contact(
            name=name, email=email,
            phone=data.get("phone", ""),
            company=data.get("company", ""),
            lead_source="Onboarding Survey",
        )
        db.session.add(contact)
        db.session.flush()

    # Collect answers
    questions = SurveyQuestion.query.filter_by(active=True).all()
    answers = {}
    for q in questions:
        answer = data.get(f"q_{q.id}", "").strip()
        if answer:
            answers[str(q.id)] = answer

    response = SurveyResponse(
        contact_id=contact.id,
        respondent_name=name,
        respondent_email=email,
        answers=json.dumps(answers),
    )
    db.session.add(response)
    log_activity("survey_submitted", f"Onboarding survey by {name}", contact_id=contact.id)
    db.session.commit()

    return render_template("public/onboarding_thanks.html", name=name)


@onboarding_bp.route("/admin")
@login_required
def admin_list():
    """Admin view of all survey responses."""
    responses = SurveyResponse.query.order_by(SurveyResponse.submitted_at.desc()).all()
    questions = {q.id: q.question_text for q in SurveyQuestion.query.all()}
    return render_template("admin/onboarding_list.html", responses=responses, questions=questions)


@onboarding_bp.route("/admin/questions", methods=["GET"])
@login_required
def admin_questions():
    questions = SurveyQuestion.query.order_by(SurveyQuestion.sort_order).all()
    return jsonify([{"id": q.id, "question_text": q.question_text, "question_type": q.question_type, "options": q.options, "sort_order": q.sort_order, "active": q.active} for q in questions])


@onboarding_bp.route("/admin/questions", methods=["POST"])
@login_required
def admin_add_question():
    data = request.get_json() or {}
    q = SurveyQuestion(
        question_text=data.get("question_text", ""),
        question_type=data.get("question_type", "text"),
        options=data.get("options", ""),
        sort_order=data.get("sort_order", 0),
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({"id": q.id}), 201


@onboarding_bp.route("/admin/questions/<int:qid>", methods=["DELETE"])
@login_required
def admin_delete_question(qid):
    q = SurveyQuestion.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    return jsonify({"deleted": True})
