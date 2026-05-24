"""AI Chatbot engine for CRM Command Center.

Uses OpenRouter API to route between Gemini 2.5 Flash (fast/cheap CRUD)
and Claude Sonnet 4 (complex reasoning).
"""
import json
import os
import requests
from extensions import db
from models import Contact, Deal, Note, ActivityLog, log_activity
from sqlalchemy import func


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FLASH_MODEL = "google/gemini-2.5-flash"
SONNET_MODEL = "anthropic/claude-sonnet-4"


def get_crm_context():
    """Build a summary of current CRM state for the AI."""
    total_contacts = Contact.query.count()
    total_leads = Contact.query.filter(Contact.status == "Lead").count()
    total_deals = Deal.query.count()

    pipeline_value = float(db.session.query(func.coalesce(func.sum(Deal.value), 0)).filter(
        Deal.stage.notin_(["Won", "Lost"])
    ).scalar())

    total_revenue = float(db.session.query(func.coalesce(func.sum(Deal.value), 0)).filter(
        Deal.stage == "Won"
    ).scalar())

    stages = ["New Lead", "Contacted", "Proposal", "Negotiation", "Won", "Lost"]
    deals_by_stage = {}
    for stage in stages:
        deals_by_stage[stage] = Deal.query.filter(Deal.stage == stage).count()

    recent_contacts = Contact.query.order_by(Contact.created_at.desc()).limit(5).all()
    recent_contacts_str = "\n".join([
        f"  - {c.name} ({c.email or 'no email'}) - {c.status} - {c.company or 'no company'}"
        for c in recent_contacts
    ])

    return f"""CRM Database Summary:
- Total Contacts: {total_contacts} ({total_leads} leads)
- Total Deals: {total_deals}
- Pipeline Value: ${pipeline_value:,.0f}
- Total Revenue (Won): ${total_revenue:,.0f}
- Deals by Stage: {json.dumps(deals_by_stage)}

Recent Contacts:
{recent_contacts_str}

Contact statuses: Lead, Customer, VIP, Inactive
Lead sources: Website Form, TikTok, Referral, Workshop, Cold Outreach, Other
Deal stages: New Lead, Contacted, Proposal, Negotiation, Won, Lost"""


SYSTEM_PROMPT = """You are an AI assistant for a CRM (Customer Relationship Management) system. You help users manage their contacts, deals, and pipeline.

You can perform these actions by responding with JSON action blocks:

1. CREATE_CONTACT: Create a new contact
   {{"action": "create_contact", "params": {{"name": "...", "email": "...", "phone": "...", "company": "...", "status": "Lead", "lead_source": "Other"}}}}

2. UPDATE_CONTACT: Update an existing contact (search by name or ID)
   {{"action": "update_contact", "params": {{"search": "name or id", "updates": {{"status": "Customer", "email": "new@email.com"}}}}}}

3. DELETE_CONTACT: Delete a contact
   {{"action": "delete_contact", "params": {{"search": "name or id"}}}}

4. CREATE_DEAL: Create a new deal
   {{"action": "create_deal", "params": {{"title": "...", "value": 50000, "stage": "New Lead", "contact_search": "contact name"}}}}

5. UPDATE_DEAL: Update a deal
   {{"action": "update_deal", "params": {{"search": "deal title or id", "updates": {{"stage": "Proposal", "value": 75000}}}}}}

6. MOVE_DEAL: Move a deal to a different stage
   {{"action": "move_deal", "params": {{"search": "deal title", "stage": "Contacted"}}}}

7. ADD_NOTE: Add a note to a contact
   {{"action": "add_note", "params": {{"contact_search": "name", "content": "Note content here"}}}}

8. QUERY: Answer questions about the CRM data (no action needed, just respond naturally)

IMPORTANT RULES:
- When performing an action, include the JSON block wrapped in ```json ... ``` in your response
- Always include a natural language explanation before or after the action
- If you're unsure about a contact or deal name, ask for clarification
- For queries about data, just answer naturally using the CRM context provided
- Contact statuses: Lead, Customer, VIP, Inactive
- Lead sources: Website Form, TikTok, Referral, Workshop, Cold Outreach, Other
- Deal stages: New Lead, Contacted, Proposal, Negotiation, Won, Lost
- Be concise and professional
- If the user's request is ambiguous, ask a clarifying question instead of guessing

{crm_context}"""


def call_openrouter(messages, model=FLASH_MODEL):
    """Call OpenRouter API."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return {"error": "OpenRouter API key not configured. Add OPENROUTER_API_KEY to your environment variables."}

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://crm-command-center.up.railway.app",
                "X-Title": "CRM Command Center",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return {"content": data["choices"][0]["message"]["content"]}
    except requests.exceptions.Timeout:
        return {"error": "AI request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"AI service error: {str(e)}"}
    except (KeyError, IndexError):
        return {"error": "Unexpected AI response format. Please try again."}


def find_contact(search_term):
    """Find a contact by name (partial match) or ID."""
    if isinstance(search_term, int) or (isinstance(search_term, str) and search_term.isdigit()):
        return Contact.query.get(int(search_term))

    # Try exact match first
    contact = Contact.query.filter(func.lower(Contact.name) == func.lower(search_term)).first()
    if contact:
        return contact

    # Try partial match
    return Contact.query.filter(Contact.name.ilike(f"%{search_term}%")).first()


def find_deal(search_term):
    """Find a deal by title (partial match) or ID."""
    if isinstance(search_term, int) or (isinstance(search_term, str) and search_term.isdigit()):
        return Deal.query.get(int(search_term))

    deal = Deal.query.filter(func.lower(Deal.title) == func.lower(search_term)).first()
    if deal:
        return deal

    return Deal.query.filter(Deal.title.ilike(f"%{search_term}%")).first()


def execute_action(action_data):
    """Execute a parsed action from the AI response."""
    action = action_data.get("action")
    params = action_data.get("params", {})

    try:
        if action == "create_contact":
            contact = Contact(
                name=params.get("name", "Unknown"),
                email=params.get("email"),
                phone=params.get("phone"),
                company=params.get("company"),
                status=params.get("status", "Lead"),
                lead_source=params.get("lead_source", "Other"),
            )
            db.session.add(contact)
            db.session.flush()
            log_activity("contact_created", f"AI created contact: {contact.name}", contact_id=contact.id)
            db.session.commit()
            return {"success": True, "message": f"Created contact: {contact.name} (ID: {contact.id})", "data": contact.to_dict()}

        elif action == "update_contact":
            contact = find_contact(params.get("search", ""))
            if not contact:
                return {"success": False, "message": f"Contact not found: {params.get('search')}"}

            updates = params.get("updates", {})
            for field, value in updates.items():
                if hasattr(contact, field) and field not in ("id", "created_at"):
                    setattr(contact, field, value)

            log_activity("contact_updated", f"AI updated contact: {contact.name}", contact_id=contact.id)
            db.session.commit()
            return {"success": True, "message": f"Updated contact: {contact.name}", "data": contact.to_dict()}

        elif action == "delete_contact":
            contact = find_contact(params.get("search", ""))
            if not contact:
                return {"success": False, "message": f"Contact not found: {params.get('search')}"}

            name = contact.name
            log_activity("contact_deleted", f"AI deleted contact: {name}")
            db.session.delete(contact)
            db.session.commit()
            return {"success": True, "message": f"Deleted contact: {name}"}

        elif action == "create_deal":
            contact = None
            if params.get("contact_search"):
                contact = find_contact(params["contact_search"])

            deal = Deal(
                title=params.get("title", "Untitled Deal"),
                value=params.get("value", 0),
                stage=params.get("stage", "New Lead"),
                contact_id=contact.id if contact else None,
            )
            db.session.add(deal)
            db.session.flush()
            log_activity("deal_created", f"AI created deal: {deal.title}", contact_id=deal.contact_id, deal_id=deal.id)
            db.session.commit()
            return {"success": True, "message": f"Created deal: {deal.title} (${deal.value:,.0f})", "data": deal.to_dict()}

        elif action == "update_deal":
            deal = find_deal(params.get("search", ""))
            if not deal:
                return {"success": False, "message": f"Deal not found: {params.get('search')}"}

            updates = params.get("updates", {})
            old_stage = deal.stage
            for field, value in updates.items():
                if hasattr(deal, field) and field not in ("id", "created_at"):
                    setattr(deal, field, value)

            if "stage" in updates and updates["stage"] != old_stage:
                log_activity("deal_moved", f"AI moved '{deal.title}' from {old_stage} to {deal.stage}", contact_id=deal.contact_id, deal_id=deal.id)
            else:
                log_activity("deal_updated", f"AI updated deal: {deal.title}", contact_id=deal.contact_id, deal_id=deal.id)
            db.session.commit()
            return {"success": True, "message": f"Updated deal: {deal.title}", "data": deal.to_dict()}

        elif action == "move_deal":
            deal = find_deal(params.get("search", ""))
            if not deal:
                return {"success": False, "message": f"Deal not found: {params.get('search')}"}

            old_stage = deal.stage
            new_stage = params.get("stage", deal.stage)
            valid_stages = ["New Lead", "Contacted", "Proposal", "Negotiation", "Won", "Lost"]
            if new_stage not in valid_stages:
                return {"success": False, "message": f"Invalid stage: {new_stage}"}

            deal.stage = new_stage
            log_activity("deal_moved", f"AI moved '{deal.title}' from {old_stage} to {new_stage}", contact_id=deal.contact_id, deal_id=deal.id)
            db.session.commit()
            return {"success": True, "message": f"Moved '{deal.title}' from {old_stage} to {new_stage}", "data": deal.to_dict()}

        elif action == "add_note":
            contact = find_contact(params.get("contact_search", ""))
            if not contact:
                return {"success": False, "message": f"Contact not found: {params.get('contact_search')}"}

            note = Note(contact_id=contact.id, content=params.get("content", ""))
            db.session.add(note)
            log_activity("note_added", f"AI added note to {contact.name}", contact_id=contact.id)
            db.session.commit()
            return {"success": True, "message": f"Added note to {contact.name}", "data": note.to_dict()}

        else:
            return {"success": False, "message": f"Unknown action: {action}"}

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Error executing action: {str(e)}"}


def extract_actions(ai_response):
    """Extract JSON action blocks from the AI's response text."""
    import re

    actions = []
    text = ai_response

    # Look for ```json ... ``` blocks
    json_blocks = re.findall(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)

    for block in json_blocks:
        try:
            action_data = json.loads(block.strip())
            if "action" in action_data:
                actions.append(action_data)
        except json.JSONDecodeError:
            continue

    # Also try to find inline JSON objects with "action" key
    if not actions:
        json_pattern = re.findall(r'\{[^{}]*"action"[^{}]*\}', text)
        for match in json_pattern:
            try:
                action_data = json.loads(match)
                if "action" in action_data:
                    actions.append(action_data)
            except json.JSONDecodeError:
                continue

    return actions


def chat(user_message, history=None):
    """Main chat function. Takes user message, returns response + actions.

    Args:
        user_message: The user's natural language input
        history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]

    Returns:
        dict with "response" (str) and "actions_taken" (list)
    """
    if not user_message.strip():
        return {"response": "Please type a message to get started.", "actions_taken": []}

    # Build messages with context
    crm_context = get_crm_context()
    system_msg = SYSTEM_PROMPT.replace("{crm_context}", crm_context)

    messages = [{"role": "system", "content": system_msg}]

    # Add conversation history (last 10 messages)
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    # Call AI
    result = call_openrouter(messages, model=FLASH_MODEL)

    if "error" in result:
        return {"response": result["error"], "actions_taken": []}

    ai_text = result["content"]

    # Extract and execute actions
    actions = extract_actions(ai_text)
    actions_taken = []

    for action_data in actions:
        action_result = execute_action(action_data)
        actions_taken.append(action_result)

    # Clean up the response (remove JSON blocks for display)
    import re
    clean_response = re.sub(r'```json\s*\n?.*?\n?\s*```', '', ai_text, flags=re.DOTALL).strip()

    # If actions were taken, append results
    if actions_taken:
        action_summaries = []
        for a in actions_taken:
            icon = "+" if a.get("success") else "x"
            action_summaries.append(f"[{icon}] {a['message']}")

        if clean_response:
            clean_response += "\n\n" + "\n".join(action_summaries)
        else:
            clean_response = "\n".join(action_summaries)

    return {"response": clean_response, "actions_taken": actions_taken}
