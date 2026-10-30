from flask import abort

from db import get_db


def get_event_or_404(event_id):
    event = get_db().execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if event is None:
        abort(404)
    return event
