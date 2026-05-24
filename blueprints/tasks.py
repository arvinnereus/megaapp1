from flask import Blueprint, render_template, request, jsonify
from extensions import db
from models import Task
from auth import login_required
from datetime import date as date_type

tasks_bp = Blueprint("tasks", __name__)

VALID_STATUSES = ["todo", "in_progress", "done"]
STATUS_DISPLAY = {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}
VALID_PRIORITIES = ["low", "medium", "high"]


@tasks_bp.route("/admin/tasks")
@login_required
def task_board():
    statuses = VALID_STATUSES
    tasks_by_status = {}
    for status in statuses:
        tasks_by_status[status] = Task.query.filter_by(status=status).order_by(Task.created_at.desc()).all()

    return render_template(
        "admin/tasks.html",
        statuses=statuses,
        tasks_by_status=tasks_by_status,
        status_display=STATUS_DISPLAY,
    )


@tasks_bp.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    status = data.get("status", "todo")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"Invalid priority. Must be one of: {VALID_PRIORITIES}"}), 400

    due_date = data.get("due_date")
    if due_date and isinstance(due_date, str):
        due_date = date_type.fromisoformat(due_date)

    task = Task(
        title=data["title"],
        description=data.get("description"),
        status=status,
        priority=priority,
        due_date=due_date,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    if "title" in data:
        task.title = data["title"]
    if "description" in data:
        task.description = data["description"]
    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400
        task.status = data["status"]
    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return jsonify({"error": f"Invalid priority. Must be one of: {VALID_PRIORITIES}"}), 400
        task.priority = data["priority"]
    if "due_date" in data:
        due_date = data["due_date"]
        if due_date and isinstance(due_date, str):
            due_date = date_type.fromisoformat(due_date)
        task.due_date = due_date

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    title = task.title
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": f"Task '{title}' deleted"})


@tasks_bp.route("/api/tasks/<int:task_id>/status", methods=["PATCH"])
@login_required
def move_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    new_status = data.get("status")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    task.status = new_status
    db.session.commit()
    return jsonify(task.to_dict())
