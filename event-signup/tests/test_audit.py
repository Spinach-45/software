import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from test_basic import app, client
from db import get_db, init_db


def add_event(app, deadline="2099-01-01T12:00", event_date="2099-01-02T12:00", closed=0):
    with app.app_context():
        db = get_db()
        result = db.execute(
            "INSERT INTO events(title,event_date,deadline,is_closed) VALUES(?,?,?,?)",
            ("測試活動", event_date, deadline, closed),
        )
        db.commit()
        return result.lastrowid


def signup(client, event_id, name="小明", phone="0912345678"):
    return client.post(f"/events/{event_id}/register", data={"name": name, "phone": phone})


@pytest.mark.parametrize("deadline", ["", "invalid", "2099-02-30T12:00", None])
def test_bad_legacy_deadline_does_not_crash(app, client, deadline):
    # NULL is not permitted by the schema; use a legacy blank value instead.
    event_id = add_event(app, deadline=deadline or "")
    response = signup(client, event_id)
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0
    assert client.get("/").status_code == 200


def test_started_event_cannot_accept_registration_even_if_deadline_is_future(app, client):
    event_id = add_event(app, event_date="2000-01-01")
    assert signup(client, event_id).status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0


def test_duplicate_identity_scope_and_count(app, client):
    first, second = add_event(app), add_event(app)
    assert signup(client, first).status_code == 302
    response = signup(client, first, " 小明 ", " 0912345678 ")
    assert "請勿重複報名" in response.get_data(as_text=True)
    assert signup(client, first, "小華").status_code == 302
    assert signup(client, first, phone="0923456789").status_code == 302
    assert signup(client, second).status_code == 302
    assert "目前報名人數：<strong>3</strong>" in client.get(f"/events/{first}/attendees").get_data(as_text=True)


def test_concurrent_duplicate_posts_create_one_row(app):
    event_id = add_event(app)
    barrier = Barrier(2)
    def submit():
        with app.test_client() as client:
            barrier.wait(timeout=10)
            return signup(client, event_id).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(statuses) == [200, 302]
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1


def test_database_rejects_duplicate_but_migration_preserves_existing_rows(app):
    event_id = add_event(app)
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO registrations(event_id,name,phone) VALUES(?,?,?)", (event_id, "小明", "0912345678"))
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO registrations(event_id,name,phone) VALUES(?,?,?)", (event_id, " 小明 ", "0912345678"))
        db.rollback()
        init_db()
        assert db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 1


def test_close_action_blocks_get_and_post_and_requires_token(app, client):
    event_id = add_event(app)
    assert client.post(f"/events/{event_id}/close").status_code == 400
    html = client.get(f"/events/{event_id}/attendees").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    response = client.post(f"/events/{event_id}/close", data={"csrf_token": token}, follow_redirects=True)
    assert "已手動關閉報名" in response.get_data(as_text=True)
    assert client.get(f"/events/{event_id}/register").status_code == 302
    assert signup(client, event_id).status_code == 302
    assert f'href="/events/{event_id}/register"' not in client.get("/").get_data(as_text=True)
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0


def test_registration_error_rolls_back_and_keeps_input(app, client):
    event_id = add_event(app)
    with app.app_context():
        db = get_db()
        db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON registrations BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
        db.commit()
    response = signup(client, event_id)
    assert response.status_code == 503
    assert 'value="小明"' in response.get_data(as_text=True)
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0
        db.execute("DROP TRIGGER fail_insert")
        db.commit()
    assert signup(client, event_id).status_code == 302


def test_new_event_database_error_preserves_form(app, client):
    with app.app_context():
        db = get_db()
        db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
        db.commit()
    response = client.post("/events/new", data={"title": "保留資料", "event_date": "2099-01-02T12:00", "deadline": "2099-01-01T12:00"})
    assert response.status_code == 503
    assert 'value="保留資料"' in response.get_data(as_text=True)


def test_read_database_failure_has_friendly_response(app, client):
    app.config["DATABASE"] = app.config["DATABASE"] + "/not-a-file"
    response = client.get("/")
    assert response.status_code == 503
    assert "資料庫暫時無法使用" in response.get_data(as_text=True)


@pytest.mark.parametrize("name,phone", [(" ", "0912345678"), ("小明", "091234567"), ("小明", "09abcdefgh"), ("小明", "０９１２３４５６７８"), ("名" * 51, "0912345678")])
def test_invalid_registration_cannot_write(app, client, name, phone):
    event_id = add_event(app)
    response = signup(client, event_id, name, phone)
    assert response.status_code == 200
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0


def test_xss_sql_and_empty_count(app, client):
    event_id = add_event(app)
    assert "目前報名人數：<strong>0</strong>" in client.get(f"/events/{event_id}/attendees").get_data(as_text=True)
    payload = "<script>alert(1)</script>' OR 1=1 --"
    assert signup(client, event_id, name=payload).status_code == 302
    html = client.get(f"/events/{event_id}/attendees").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("path,status", [("/events/no/register", 404), ("/events/-1/attendees", 404), ("/events/999/attendees", 404), ("/events/1/close", 405)])
def test_invalid_paths_have_return_link(client, path, status):
    response = client.get(path)
    assert response.status_code == status
    assert "返回活動清單" in response.get_data(as_text=True)
