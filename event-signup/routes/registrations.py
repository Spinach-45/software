import re

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from db import get_db
from routes import get_event_or_404


bp = Blueprint("registrations", __name__)


@bp.route(
    "/events/<int:event_id>/register",
    methods=["GET", "POST"],
)
def register(event_id):
    event = get_event_or_404(event_id)

    form = {"name": "", "phone": ""}
    errors = {}

    if request.method == "POST":
        form = {
            key: request.form.get(key, "").strip()
            for key in form
        }

        # 檢查姓名
        if not form["name"]:
            errors["name"] = "請輸入姓名"
        elif len(form["name"]) > 50:
            errors["name"] = "姓名請勿超過 50 個字"

        # 檢查手機號碼
        if not form["phone"]:
            errors["phone"] = "請輸入聯絡電話"
        elif not re.fullmatch(r"09[0-9]{8}", form["phone"]):
            errors["phone"] = "請輸入 09 開頭的 10 碼手機號碼"

        if not errors:
            db = get_db()

            # SQLite：先取得寫入鎖，避免同時送出造成重複報名。
            db.execute("BEGIN IMMEDIATE")

            try:
                existing = db.execute(
                    """
                    SELECT 1
                    FROM registrations
                    WHERE event_id = ? AND phone = ?
                    LIMIT 1
                    """,
                    (event_id, form["phone"]),
                ).fetchone()

                if existing:
                    db.rollback()
                    errors["phone"] = "這個手機號碼已報名此活動，請勿重複報名"
                else:
                    db.execute(
                        """
                        INSERT INTO registrations
                            (event_id, name, phone)
                        VALUES (?, ?, ?)
                        """,
                        (
                            event_id,
                            form["name"],
                            form["phone"],
                        ),
                    )
                    db.commit()

                    flash("報名成功！期待與你一起參加活動。", "success")
                    return redirect(url_for("events.index"))

            except Exception:
                db.rollback()
                raise

    return render_template(
        "register/form.html",
        event=event,
        form=form,
        errors=errors,
    )