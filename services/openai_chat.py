"""Jackie AI — provider-agnostic chat (OpenAI direct or OpenRouter)."""
import os
from openai import OpenAI

JACKIE_SYSTEM_PROMPT = """You are Jackie, a friendly and knowledgeable AI business assistant.
You help small business owners with marketing, operations, customer management, and growth strategy.
Keep responses concise and actionable — 2-4 paragraphs max.
Use a warm, professional tone. You're like a smart friend who happens to know business.
If asked about technical setup, guide them step by step.
Always be encouraging — these are hardworking small business owners."""


def get_ai_client():
    """Return (OpenAI client, model_name) based on configured provider."""
    provider = os.getenv("CHAT_PROVIDER", "openai")
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None, None
        return OpenAI(api_key=api_key), os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    else:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return None, None
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={"HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000")},
        ), "google/gemini-2.5-flash"


def jackie_chat(user_message, history=None):
    """Send a message to Jackie and get a response."""
    client, model = get_ai_client()
    if not client:
        return {
            "response": "Jackie is not configured yet. Add your OPENAI_API_KEY or OPENROUTER_API_KEY in Settings to activate me!",
            "provider": "demo",
        }
    messages = [{"role": "system", "content": JACKIE_SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})
    try:
        resp = client.chat.completions.create(model=model, messages=messages, max_tokens=1024, temperature=0.4)
        return {"response": resp.choices[0].message.content, "provider": os.getenv("CHAT_PROVIDER", "openrouter")}
    except Exception as e:
        return {"response": f"Sorry, I hit an error: {str(e)}", "provider": "error"}
