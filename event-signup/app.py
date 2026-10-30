import os

from flask import Flask

import db
from routes.attendees import bp as attendees_bp
from routes.events import bp as events_bp
from routes.registrations import bp as registrations_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        DATABASE=os.path.join(app.root_path, "event_signup.db"),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(attendees_bp)

    return app
