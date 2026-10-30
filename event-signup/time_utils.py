"""所有活動時間以台灣時間處理；舊的純日期視為當日 00:00。"""
import re
from datetime import datetime, timedelta, timezone

TAIWAN_TIME = timezone(timedelta(hours=8))


def now_taiwan():
    return datetime.now(TAIWAN_TIME)


def parse_time(value, *, form_input=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing date")
    value = value.strip()
    if form_input and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", value):
        raise ValueError("expected YYYY-MM-DDTHH:MM")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TAIWAN_TIME)
    return parsed.astimezone(TAIWAN_TIME)


def registration_status(event, now=None):
    if event["is_closed"]:
        return "已手動關閉報名"
    try:
        start, deadline = parse_time(event["event_date"]), parse_time(event["deadline"])
        if deadline > start:
            return "時間資料異常，暫停報名"
        now = now if now is not None else now_taiwan()
        if now >= deadline or now >= start:
            return "已截止報名"
    except (ValueError, TypeError, OverflowError):
        return "時間資料異常，暫停報名"
    return "開放報名"


def registration_closed(event):
    return registration_status(event) != "開放報名"


def display_time(value):
    try:
        return parse_time(value).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError, OverflowError):
        return "時間資料異常"
