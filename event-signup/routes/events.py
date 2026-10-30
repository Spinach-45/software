import secrets
import sqlite3
from datetime import timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from db import get_db
from routes import get_event_or_404
from time_utils import now_taiwan, parse_time

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
    status = 200
    now = now_taiwan()

    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in form}
        if not form["title"]:
            errors["title"] = "請輸入活動名稱"
        elif len(form["title"].encode("utf-16-le")) // 2 > 100:
            errors["title"] = "活動名稱請勿超過 100 個字元"
        if len(form["description"].encode("utf-16-le")) // 2 > 2000:
            errors["description"] = "活動說明請勿超過 2000 個字元"
        if not form["event_date"]:
            errors["event_date"] = "請選擇活動時間"
        if not form["deadline"]:
            errors["deadline"] = "請選擇截止報名時間"

        times = {}
        for field, label in (("event_date", "活動時間"), ("deadline", "截止報名時間")):
            if not form[field]:
                continue
            try:
                times[field] = parse_time(form[field], form_input=True)
            except (ValueError, OverflowError):
                errors[field] = f"請輸入有效的{label}"

        if "event_date" in times and times["event_date"] < now:
            errors["event_date"] = "活動時間不能早於現在"
        if "deadline" in times and times["deadline"] < now:
            errors["deadline"] = "報名截止時間不能早於現在"
        if ("event_date" in times and "deadline" in times
                and times["deadline"] > times["event_date"]):
            errors.setdefault("deadline", "報名截止時間不能晚於活動時間")

        if not errors:
            db = get_db()
            try:
                db.execute("BEGIN IMMEDIATE")
                # 可能等待其他寫入釋放鎖；取得鎖後重新確認現在時間。
                now = now_taiwan()
                if times["event_date"] < now:
                    errors["event_date"] = "活動時間不能早於現在"
                if times["deadline"] < now:
                    errors["deadline"] = "報名截止時間不能早於現在"
                if errors:
                    db.rollback()
                else:
                    db.execute(
                        "INSERT INTO events (title, description, event_date, deadline)"
                        " VALUES (?, ?, ?, ?)",
                        (form["title"], form["description"], form["event_date"], form["deadline"]),
                    )
                    db.commit()
                    flash("活動新增成功", "success")
                    return redirect(url_for("events.index"))
            except sqlite3.Error:
                db.rollback()
                current_app.logger.exception("Creating event failed")
                errors["database"] = "資料庫暫時無法使用，未新增活動。請稍後重試。"
                status = 503

    # 分鐘精度的選擇器，向上取整，避免選到已經過去的秒數。
    minimum = now.replace(second=0, microsecond=0)
    if minimum < now:
        minimum += timedelta(minutes=1)
    return render_template("events/new.html", form=form, errors=errors,
                           min_datetime=minimum.strftime("%Y-%m-%dT%H:%M"),
                           server_now=now.isoformat()), status


@bp.post("/events/<int:event_id>/close")
def close(event_id):
    token = request.form.get("csrf_token", "")
    if not token or not secrets.compare_digest(token.encode("utf-8"), session.get("close_token", "").encode("utf-8")):
        abort(400)
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        get_event_or_404(event_id)
        db.execute("UPDATE events SET is_closed = 1 WHERE id = ?", (event_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise
    flash("已手動關閉報名。", "success")
    return redirect(url_for("attendees.list_attendees", event_id=event_id))
