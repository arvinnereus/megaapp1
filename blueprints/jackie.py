"""Jackie AI assistant — full-page chat interface + voice mode."""
import os

import requests
from flask import Blueprint, render_template, request, jsonify

from auth import login_required
from services.openai_chat import jackie_chat

jackie_bp = Blueprint("jackie", __name__)


JACKIE_VOICE_INSTRUCTIONS = (
    "You are Jackie, a friendly AI business assistant for small business owners. "
    "This is a voice conversation, so keep replies short — 1 to 3 sentences max. "
    "Talk naturally with contractions ('I'd', 'you're', 'let's'). "
    "Help with marketing, operations, customer management, and growth strategy. "
    "Be warm, encouraging, and practical."
)


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


@jackie_bp.route("/api/voice/token", methods=["POST"])
@login_required
def voice_token():
    """
    Mint a short-lived OpenAI Realtime session token for the browser.

    The browser uses it (over WebRTC) to stream audio directly to OpenAI.
    The real OPENAI_API_KEY never leaves the server.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({
            "error": "OPENAI_API_KEY is not set — voice mode needs an OpenAI key with Realtime access."
        }), 400

    model = os.environ.get("REALTIME_MODEL", "gpt-realtime")
    voice = os.environ.get("REALTIME_VOICE", "alloy")

    try:
        r = requests.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "session": {
                    "type": "realtime",
                    "model": model,
                    "instructions": JACKIE_VOICE_INSTRUCTIONS,
                    "audio": {"output": {"voice": voice}},
                }
            },
            timeout=15,
        )
    except requests.RequestException as e:
        return jsonify({"error": f"Could not reach OpenAI: {e}"}), 502

    if r.status_code != 200:
        return jsonify({
            "error": f"OpenAI rejected the session request (HTTP {r.status_code}): {r.text[:300]}"
        }), r.status_code

    # Normalize to the shape the browser JS expects: { value, model, expires_at }
    data = r.json()
    return jsonify({
        "value": data.get("value"),
        "model": (data.get("session") or {}).get("model", model),
        "expires_at": data.get("expires_at"),
    })
