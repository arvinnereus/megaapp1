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
