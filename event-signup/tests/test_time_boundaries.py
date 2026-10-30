from datetime import datetime

import pytest

from test_basic import app, client
import time_utils
import routes.events as event_routes
from db import get_db
from test_audit import add_event, signup


@pytest.mark.parametrize("now,allowed", [
    ("2030-01-01T11:59:59.999999+08:00", True),
    ("2030-01-01T12:00:00+08:00", False),
    ("2030-01-01T12:00:00.000001+08:00", False),
])
def test_deadline_instant_blocks_get_and_post(app, client, monkeypatch, now, allowed):
    monkeypatch.setattr(time_utils, "now_taiwan", lambda: datetime.fromisoformat(now))
    event_id = add_event(app, deadline="2030-01-01T04:00:00+00:00", event_date="2030-01-02")
    assert client.get(f"/events/{event_id}/register").status_code == (200 if allowed else 302)
    assert signup(client, event_id).status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == int(allowed)


@pytest.mark.parametrize("now,allowed", [
    ("2030-01-01T23:59:59+08:00", True),
    ("2030-01-02T00:00:00+08:00", False),
    ("2030-01-02T09:00:00+08:00", False),
])
def test_legacy_date_only_is_midnight(app, client, monkeypatch, now, allowed):
    monkeypatch.setattr(time_utils, "now_taiwan", lambda: datetime.fromisoformat(now))
    event_id = add_event(app, event_date="2030-01-02", deadline="2030-01-02")
    signup(client, event_id)
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == int(allowed)


@pytest.mark.parametrize("date", ["", "2099-01-01", "2099-01-01T12:00+08:00", "2099-02-30T12:00", "2099-01-01T25:00"])
def test_new_event_requires_valid_local_datetime(app, client, date):
    response = client.post("/events/new", data={"title": "活動", "event_date": date, "deadline": "2099-01-01T12:00"})
    assert response.status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_migration_keeps_legacy_duplicates_and_blocks_new_ones(app):
    event_id = add_event(app)
    with app.app_context():
        db = get_db()
        db.execute("DROP TRIGGER registrations_no_duplicate_insert")
        db.executemany("INSERT INTO registrations(event_id,name,phone) VALUES(?,?,?)", [(event_id, "小明", "0912345678")] * 2)
        db.commit()
    runner = app.test_cli_runner()
    result = runner.invoke(args=["migrate-db"])
    assert result.exit_code == 0
    assert runner.invoke(args=["migrate-db"]).exit_code == 0
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 2
    with app.test_client() as client:
        assert "請勿重複報名" in signup(client, event_id).get_data(as_text=True)


def test_large_url_parameter_is_404(client):
    assert client.get("/events/9999999999999999999999999999999/register").status_code == 404


def test_attendee_timestamp_is_taiwan_not_host_local(app, client):
    event_id = add_event(app)
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO registrations(event_id,name,phone,created_at) VALUES(?,?,?,?)", (event_id, "小明", "0912345678", "2030-01-01 20:30:00"))
        db.commit()
    assert "2030-01-02 04:30:00" in client.get(f"/events/{event_id}/attendees").get_data(as_text=True)


def test_creation_rechecks_time_after_waiting_for_database_lock(app, client, monkeypatch):
    clock = iter([datetime.fromisoformat("2030-01-01T11:59:59+08:00"),
                  datetime.fromisoformat("2030-01-01T12:00:01+08:00")])
    monkeypatch.setattr(event_routes, "now_taiwan", lambda: next(clock))
    response = client.post("/events/new", data={"title": "活動", "event_date": "2030-01-01T13:00", "deadline": "2030-01-01T12:00"})
    assert "報名截止時間不能早於現在" in response.get_data(as_text=True)
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_registration_rechecks_deadline_after_lock(app, client, monkeypatch):
    clock = iter([datetime.fromisoformat("2030-01-01T11:59:59+08:00"),
                  datetime.fromisoformat("2030-01-01T12:00:00+08:00")])
    monkeypatch.setattr(time_utils, "now_taiwan", lambda: next(clock))
    event_id = add_event(app, deadline="2030-01-01T12:00", event_date="2030-01-02")
    assert signup(client, event_id).status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0


def test_invalid_close_token_is_not_server_error(app, client):
    event_id = add_event(app)
    assert client.post(f"/events/{event_id}/close", data={"csrf_token": "錯誤"}).status_code == 400
