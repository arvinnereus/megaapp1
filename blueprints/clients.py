from flask import Blueprint, render_template, request, jsonify
from extensions import db
from models import Contact, ClientNote, Deal, Purchase, log_activity
from auth import login_required

clients_bp = Blueprint("clients", __name__)


# ── Pages ──────────────────────────────────────────────────────────────

@clients_bp.route("/admin/clients")
@login_required
def clients_list():
    archived = request.args.get("archived", "").lower() == "true"
    if archived:
        clients = Contact.query.filter(Contact.status.in_(["Archived"])).order_by(Contact.created_at.desc()).all()
    else:
        clients = Contact.query.filter(Contact.status.in_(["Client", "Customer"])).order_by(Contact.created_at.desc()).all()
    return render_template("admin/clients.html", clients=clients, archived=archived)


@clients_bp.route("/admin/clients/<int:id>")
@login_required
def client_detail(id):
    client = Contact.query.get_or_404(id)
    deals = Deal.query.filter_by(contact_id=id).order_by(Deal.created_at.desc()).all()
    purchases = Purchase.query.filter_by(contact_id=id).order_by(Purchase.purchased_at.desc()).all()
    return render_template("admin/client_detail.html", client=client, deals=deals, purchases=purchases)


# ── API ────────────────────────────────────────────────────────────────

@clients_bp.route("/api/clients/<int:id>/notes", methods=["POST"])
@login_required
def add_client_note(id):
    client = Contact.query.get_or_404(id)
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    note = ClientNote(contact_id=client.id, title=title, content=content)
    db.session.add(note)
    log_activity("note_added", f"Client note added for {client.name}: {title}", contact_id=client.id)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@clients_bp.route("/api/clients/<int:id>/notes/<int:note_id>", methods=["PUT"])
@login_required
def edit_client_note(id, note_id):
    client = Contact.query.get_or_404(id)
    note = ClientNote.query.get_or_404(note_id)
    if note.contact_id != client.id:
        return jsonify({"error": "Note does not belong to this client"}), 403

    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    note.title = title
    note.content = content
    log_activity("note_updated", f"Client note updated for {client.name}: {title}", contact_id=client.id)
    db.session.commit()
    return jsonify(note.to_dict())


@clients_bp.route("/api/clients/<int:id>/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_client_note(id, note_id):
    client = Contact.query.get_or_404(id)
    note = ClientNote.query.get_or_404(note_id)
    if note.contact_id != client.id:
        return jsonify({"error": "Note does not belong to this client"}), 403

    db.session.delete(note)
    log_activity("note_deleted", f"Client note deleted for {client.name}: {note.title}", contact_id=client.id)
    db.session.commit()
    return jsonify({"success": True})


@clients_bp.route("/api/clients/<int:id>/archive", methods=["PATCH"])
@login_required
def toggle_archive_client(id):
    client = Contact.query.get_or_404(id)
    if client.status == "Archived":
        client.status = "Client"
        log_activity("status_changed", f"{client.name} unarchived (status set to Client)", contact_id=client.id)
    else:
        client.status = "Archived"
        log_activity("status_changed", f"{client.name} archived", contact_id=client.id)
    db.session.commit()
    return jsonify(client.to_dict())
