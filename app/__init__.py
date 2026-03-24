import os
from flask import Flask
from app.models.models import db


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///placement.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "..", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    if config:
        app.config.update(config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from app.routes.main      import main_bp
    from app.routes.auth      import auth_bp
    from app.routes.drive     import drive_bp
    from app.routes.student   import student_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(drive_bp,     url_prefix="/drives")
    app.register_blueprint(student_bp,   url_prefix="/students")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    with app.app_context():
        db.create_all()
        # create default placement cell admin on first run
        from app.services.auth_service import create_default_admin
        create_default_admin(db.session)

    return app
