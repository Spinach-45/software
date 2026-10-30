import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import get_db, init_db  # noqa: E402


@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({"TESTING": True, "DATABASE": db_path})
    with app.app_context():
        init_db()
    yield app
    os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_event_register_and_list(app, client):
    # 新增活動
    resp = client.post(
        "/events/new",
        data={
            "title": "程式讀書會",
            "description": "每週一次",
            "event_date": "2026-12-01",
            "deadline": "2026-11-25T18:00",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "程式讀書會" in resp.get_data(as_text=True)

    with app.app_context():
        event_id = get_db().execute("SELECT id FROM events").fetchone()["id"]

    # 報名
    resp = client.post(
        f"/events/{event_id}/register",
        data={"name": "王小明", "phone": "0912345678"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "報名成功" in resp.get_data(as_text=True)

    # 報名清單出現該筆，人數為 1
    resp = client.get(f"/events/{event_id}/attendees")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "王小明" in html
    assert "0912345678" in html
    assert "目前報名人數：<strong>1</strong>" in html


def test_register_validation_keeps_input(app, client):
    client.post(
        "/events/new",
        data={"title": "A", "event_date": "2026-12-01", "deadline": "2026-11-25T18:00"},
    )
    resp = client.post("/events/1/register", data={"name": "小華", "phone": "  "})
    html = resp.get_data(as_text=True)
    assert "請輸入聯絡電話" in html
    assert 'value="小華"' in html
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 0


def test_seed_db_runs_once(app, client):
    runner = app.test_cli_runner()
    assert "已寫入" in runner.invoke(args=["seed-db"]).output
    assert "略過" in runner.invoke(args=["seed-db"]).output

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0] == 3

    assert "Python 入門工作坊" in client.get("/").get_data(as_text=True)


def test_missing_event_returns_404(client):
    assert client.get("/events/999/register").status_code == 404
    assert client.get("/events/999/attendees").status_code == 404
