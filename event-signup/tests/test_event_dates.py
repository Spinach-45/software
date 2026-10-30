import pytest

from test_basic import app, client
from db import get_db


@pytest.mark.parametrize("event_date,deadline,message", [
    ("2000-01-01T12:00", "2099-01-01T12:00", "活動時間不能早於現在"),
    ("2099-01-01T12:00", "2000-01-01T12:00", "報名截止時間不能早於現在"),
    ("2099-01-01T12:00", "2099-01-01T12:01", "報名截止時間不能晚於活動時間"),
    ("invalid", "2099-01-01T12:00", "請輸入有效的活動時間"),
    ("2099-01-01T12:00", "2099-02-30T12:00", "請輸入有效的截止報名時間"),
])
def test_invalid_dates_do_not_create_event(app, client, event_date, deadline, message):
    response = client.post("/events/new", data={
        "title": "測試活動", "event_date": event_date, "deadline": deadline,
    })
    assert message in response.get_data(as_text=True)
    assert 'value="測試活動"' in response.get_data(as_text=True)
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


@pytest.mark.parametrize("deadline", ["2099-01-01T11:00", "2099-01-01T12:00"])
def test_valid_dates_create_event(app, client, deadline):
    response = client.post("/events/new", data={
        "title": "測試活動", "event_date": "2099-01-01T12:00", "deadline": deadline,
    })
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_form_has_browser_constraints(client):
    html = client.get("/events/new").get_data(as_text=True)
    assert 'novalidate' not in html
    assert html.count('type="datetime-local"') == 2
    assert 'min="' in html
