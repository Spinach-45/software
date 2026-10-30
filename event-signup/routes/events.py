from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_db

bp = Blueprint("events", __name__)


@bp.get("/")
def index():
    events = get_db().execute(
        """
        SELECT e.*, COUNT(r.id) AS signup_count
        FROM events e
        LEFT JOIN registrations r ON r.event_id = e.id
        GROUP BY e.id
        ORDER BY e.event_date, e.id
        """
    ).fetchall()
    return render_template("events/list.html", events=events)


@bp.route("/events/new", methods=["GET", "POST"])
def new():
    form = {"title": "", "description": "", "event_date": "", "deadline": ""}
    errors = {}

    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in form}
        if not form["title"]:
            errors["title"] = "請輸入活動名稱"
        if not form["event_date"]:
            errors["event_date"] = "請選擇活動日期"
        if not form["deadline"]:
            errors["deadline"] = "請選擇截止報名時間"

        if not errors:
            db = get_db()
            db.execute(
                "INSERT INTO events (title, description, event_date, deadline)"
                " VALUES (?, ?, ?, ?)",
                (form["title"], form["description"], form["event_date"], form["deadline"]),
            )
            db.commit()
            flash("活動新增成功", "success")
            return redirect(url_for("events.index"))

    return render_template("events/new.html", form=form, errors=errors)
