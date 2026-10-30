import sqlite3
from datetime import timedelta

import click
from flask import current_app, g
from flask.cli import with_appcontext
from time_utils import now_taiwan


def get_db():
    """取得目前請求共用的資料庫連線。"""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=5)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    migrate_db()


def migrate_db():
    """只新增索引與保護觸發器，不清理或刪除既有資料。"""
    db = get_db()
    try:
        with current_app.open_resource("migration.sql") as source:
            db.executescript("BEGIN IMMEDIATE;\n" + source.read().decode("utf-8") + "\nCOMMIT;")
    except sqlite3.Error:
        db.rollback()
        raise


SAMPLE_EVENTS = [
    {
        "title": "Python 入門工作坊",
        "description": "從零開始學 Python，請自備筆電。",
        "event_date": "2026-12-05",
        "deadline": "2026-11-30T23:59",
        "attendees": [("王小明", "0912345678"), ("李小華", "0923456789")],
    },
    {
        "title": "期末專題成果發表會",
        "description": "各組展示期末專題，歡迎旁聽。",
        "event_date": "2026-12-20",
        "deadline": "2026-12-15T18:00",
        "attendees": [("陳大文", "0934567890")],
    },
    {
        "title": "寒假登山健行",
        "description": "",
        "event_date": "2027-01-18",
        "deadline": "2027-01-10T12:00",
        "attendees": [],
    },
]


def seed_db():
    """寫入範例資料。資料庫已經有活動時不做任何事，回傳是否有寫入。"""
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0:
        return False

    today = now_taiwan().date()
    for offset, event in enumerate(SAMPLE_EVENTS):
        start = today + timedelta(days=30 + offset * 15)
        cur = db.execute(
            "INSERT INTO events (title, description, event_date, deadline)"
            " VALUES (?, ?, ?, ?)",
            (event["title"], event["description"], f"{start}T14:00", f"{start - timedelta(days=1)}T18:00"),
        )
        db.executemany(
            "INSERT INTO registrations (event_id, name, phone) VALUES (?, ?, ?)",
            [(cur.lastrowid, name, phone) for name, phone in event["attendees"]],
        )
    db.commit()
    return True


@click.command("init-db")
@with_appcontext
def init_db_command():
    """建立資料表。"""
    init_db()
    click.echo("資料庫初始化完成。")


@click.command("migrate-db")
@with_appcontext
def migrate_db_command():
    """為既有資料庫新增重複報名保護，保留所有資料。"""
    try:
        migrate_db()
    except sqlite3.Error as error:
        raise click.ClickException("遷移失敗，已回滾。請確認已初始化資料庫並稍後重試。") from error
    click.echo("資料庫遷移完成，既有資料保留。")


@click.command("seed-db")
@with_appcontext
def seed_db_command():
    """建立資料表並寫入範例資料。"""
    init_db()
    if seed_db():
        click.echo(f"已寫入 {len(SAMPLE_EVENTS)} 筆範例活動。")
    else:
        click.echo("資料庫已經有活動，略過範例資料。")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)
    app.cli.add_command(seed_db_command)
