import os
import secrets
import sqlite3

from flask import Flask, current_app, g, render_template, session
from werkzeug.exceptions import HTTPException

import db
from routes.attendees import bp as attendees_bp
from routes.events import bp as events_bp
from routes.registrations import bp as registrations_bp
from time_utils import display_time, registration_closed, registration_status


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        DATABASE=os.path.join(app.root_path, "event_signup.db"),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(attendees_bp)

    def csrf_token():
        if "close_token" not in session:
            session["close_token"] = secrets.token_urlsafe(32)
        return session["close_token"]

    app.jinja_env.globals.update(registration_closed=registration_closed,
                                 registration_status=registration_status,
                                 csrf_token=csrf_token)
    app.jinja_env.filters["taiwan_time"] = display_time

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        connection = g.get("db")
        if connection is not None:
            connection.rollback()
        current_app.logger.exception("Database operation failed")
        return render_template("error.html", code=503,
                               message="資料庫暫時無法使用，請稍後重試；若尚未初始化，請執行 init-db。"), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: "請求資料無效，請返回頁面後重新操作。", 404: "找不到此活動或頁面。",
                    405: "此操作不支援目前的請求方式。", 413: "送出的資料過大，請縮短內容後重試。"}
        return render_template("error.html", code=error.code,
                               message=messages.get(error.code, "操作無法完成，請稍後重試。")), error.code

    return app
