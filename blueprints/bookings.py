"""Calendar booking system — admin calendar + public booking page."""
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify
from auth import login_required
from extensions import db
from models import Booking, BookingSlot, Contact, log_activity

bookings_bp = Blueprint("bookings", __name__)


# -- Admin: Calendar View -----------------------------------------------
@bookings_bp.route("/")
@login_required
def index():
    return render_template("admin/bookings.html")


@bookings_bp.route("/api/events")
@login_required
def api_events():
    """JSON feed for FullCalendar -- returns all bookings as events."""
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    query = Booking.query
    if start:
        query = query.filter(Booking.date >= start[:10])
    if end:
        query = query.filter(Booking.date <= end[:10])
    events = []
    for b in query.all():
        color = {"confirmed": "#C7A35A", "cancelled": "#ef4444", "completed": "#10b981"}.get(b.status, "#C7A35A")
        events.append({
            "id": b.id,
            "title": f"{b.client_name} — {b.slot_type}",
            "start": f"{b.date.isoformat()}T{b.start_time}",
            "end": f"{b.date.isoformat()}T{b.end_time}",
            "color": color,
            "extendedProps": {
                "email": b.client_email,
                "phone": b.client_phone,
                "status": b.status,
                "notes": b.notes,
            },
        })
    return jsonify(events)


# -- Admin: Manage Slots ------------------------------------------------
@bookings_bp.route("/api/slots", methods=["GET"])
@login_required
def api_list_slots():
    slots = BookingSlot.query.filter_by(active=True).order_by(BookingSlot.day_of_week, BookingSlot.start_time).all()
    return jsonify([{
        "id": s.id, "day_of_week": s.day_of_week,
        "start_time": s.start_time, "end_time": s.end_time,
        "slot_type": s.slot_type, "active": s.active,
    } for s in slots])


@bookings_bp.route("/api/slots", methods=["POST"])
@login_required
def api_create_slot():
    data = request.get_json() or {}
    slot = BookingSlot(
        day_of_week=data.get("day_of_week", 0),
        start_time=data.get("start_time", "09:00"),
        end_time=data.get("end_time", "10:00"),
        slot_type=data.get("slot_type", "consultation"),
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify({"id": slot.id}), 201


@bookings_bp.route("/api/slots/<int:slot_id>", methods=["DELETE"])
@login_required
def api_delete_slot(slot_id):
    slot = BookingSlot.query.get_or_404(slot_id)
    db.session.delete(slot)
    db.session.commit()
    return jsonify({"deleted": True})


# -- Public: Available Slots for a Date ----------------------------------
@bookings_bp.route("/api/available")
def api_available():
    """Return available time slots for a given date."""
    date_str = request.args.get("date", "")
    if not date_str:
        return jsonify([])
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify([]), 400

    day_of_week = target_date.weekday()
    slots = BookingSlot.query.filter_by(day_of_week=day_of_week, active=True).all()

    # Filter out already-booked slots
    booked = Booking.query.filter_by(date=target_date).filter(
        Booking.status != "cancelled"
    ).all()
    booked_times = {(b.start_time, b.end_time) for b in booked}

    available = []
    for s in slots:
        if (s.start_time, s.end_time) not in booked_times:
            available.append({
                "start_time": s.start_time,
                "end_time": s.end_time,
                "slot_type": s.slot_type,
            })
    return jsonify(available)


# -- Public: Book an Appointment -----------------------------------------
@bookings_bp.route("/api/book", methods=["POST"])
def api_book():
    """Create a booking (public, no auth required)."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    if not name or not email or not data.get("date") or not data.get("start_time"):
        return jsonify({"error": "Name, email, date, and time slot are required"}), 400

    try:
        booking_date = date.fromisoformat(data["date"])
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    # Check slot is still available
    existing = Booking.query.filter_by(
        date=booking_date, start_time=data["start_time"]
    ).filter(Booking.status != "cancelled").first()
    if existing:
        return jsonify({"error": "This time slot is no longer available"}), 409

    # Find or create contact
    contact = Contact.query.filter_by(email=email).first()
    if not contact:
        contact = Contact(name=name, email=email, phone=data.get("phone", ""), lead_source="Booking")
        db.session.add(contact)
        db.session.flush()

    booking = Booking(
        contact_id=contact.id,
        client_name=name,
        client_email=email,
        client_phone=data.get("phone", ""),
        date=booking_date,
        start_time=data["start_time"],
        end_time=data.get("end_time", ""),
        slot_type=data.get("slot_type", "consultation"),
        notes=data.get("notes", ""),
    )
    db.session.add(booking)
    log_activity("booking_created", f"Booking by {name} on {booking_date}", contact_id=contact.id)
    db.session.commit()

    return jsonify({"id": booking.id, "status": "confirmed"}), 201


# -- Public: Booking Page ------------------------------------------------
@bookings_bp.route("/book")
def public_book():
    return render_template("public/book.html")


# -- Admin: Update Booking Status ----------------------------------------
@bookings_bp.route("/api/<int:booking_id>/status", methods=["PATCH"])
@login_required
def api_update_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json() or {}
    new_status = data.get("status", booking.status)
    if new_status in ("confirmed", "cancelled", "completed"):
        booking.status = new_status
        db.session.commit()
    return jsonify({"id": booking.id, "status": booking.status})
