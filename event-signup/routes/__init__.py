from flask import abort

from db import get_db


def get_event_or_404(event_id):
    # SQLite INTEGER 為有號 64 位元；超大網址參數不應造成 OverflowError。
    if not 1 <= event_id <= 9223372036854775807:
        abort(404)
    event = get_db().execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if event is None:
        abort(404)
    return event
