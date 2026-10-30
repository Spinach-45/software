from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db
from routes import get_event_or_404

bp = Blueprint("registrations", __name__)


@bp.route("/events/<int:event_id>/register", methods=["GET", "POST"])
def register(event_id):
    event = get_event_or_404(event_id)
    form = {"name": "", "phone": ""}
    errors = {}

    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in form}
        if not form["name"]:
            errors["name"] = "請輸入姓名"
        if not form["phone"]:
            errors["phone"] = "請輸入聯絡電話"

        if not errors:
            db = get_db()
            db.execute(
                "INSERT INTO registrations (event_id, name, phone) VALUES (?, ?, ?)",
                (event_id, form["name"], form["phone"]),
            )
            db.commit()
            flash("報名成功", "success")
            return redirect(url_for("events.index"))

    return render_template("register/form.html", event=event, form=form, errors=errors)
