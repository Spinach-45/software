import re
import sqlite3

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from db import get_db
from routes import get_event_or_404
from time_utils import registration_closed


bp = Blueprint("registrations", __name__)

@bp.route(
    "/events/<int:event_id>/register",
    methods=["GET", "POST"],
)
def register(event_id):
    event = get_event_or_404(event_id)

    # 直接輸入網址或送出表單，也會檢查截止時間
    if registration_closed(event):
        flash("此活動已截止報名。", "error")
        return redirect(url_for("events.index"))

    form = {"name": "", "phone": ""}
    errors = {}
    status = 200

    if request.method == "POST":
        form = {
            key: request.form.get(key, "").strip()
            for key in form
        }

        if not form["name"]:
            errors["name"] = "請輸入姓名"
        elif len(form["name"].encode("utf-16-le")) // 2 > 50:
            errors["name"] = "姓名請勿超過 50 個字"

        if not form["phone"]:
            errors["phone"] = "請輸入聯絡電話"
        elif not re.fullmatch(r"09[0-9]{8}", form["phone"]):
            errors["phone"] = "請輸入 09 開頭的 10 碼手機號碼"

        if not errors:
            db = get_db()

            try:
                db.execute("BEGIN IMMEDIATE")

                # 取得鎖後重新讀取活動，確認最新截止狀態
                event = get_event_or_404(event_id)

                if registration_closed(event):
                    db.rollback()
                    flash("此活動已截止報名。", "error")
                    return redirect(url_for("events.index"))

                # 同一活動：姓名及電話都相同，才算重複報名
                existing = db.execute(
                    """
                    SELECT 1
                    FROM registrations
                    WHERE event_id = ?
                      AND trim(name) = ?
                      AND trim(phone) = ?
                    LIMIT 1
                    """,
                    (
                        event_id,
                        form["name"],
                        form["phone"],
                    ),
                ).fetchone()

                if existing:
                    db.rollback()
                    errors["phone"] = "相同姓名與電話已報名此活動，請勿重複報名"
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

            except sqlite3.Error as error:
                db.rollback()
                if isinstance(error, sqlite3.IntegrityError) and str(error) == "duplicate registration":
                    errors["phone"] = "相同姓名與電話已報名此活動，請勿重複報名"
                else:
                    current_app.logger.exception("Registration failed")
                    errors["database"] = "資料庫暫時無法使用，未新增報名。請稍後重試。"
                    status = 503
            except Exception:
                db.rollback()
                raise

    return render_template(
        "register/form.html",
        event=event,
        form=form,
        errors=errors,
    ), status
