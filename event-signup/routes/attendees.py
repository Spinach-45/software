from flask import Blueprint, render_template

from db import get_db
from routes import get_event_or_404

bp = Blueprint("attendees", __name__)


@bp.get("/events/<int:event_id>/attendees")
def list_attendees(event_id):
    event = get_event_or_404(event_id)
    db = get_db()
    # created_at 以 UTC 儲存，固定顯示台灣時間，不依賴主機時區。
    attendees = db.execute(
        "SELECT name, phone, datetime(created_at, '+8 hours') AS created_at"
        " FROM registrations WHERE event_id = ? ORDER BY id",
        (event_id,),
    ).fetchall()
    count = len(attendees)
    return render_template(
        "attendees/list.html", event=event, attendees=attendees, count=count
    )
