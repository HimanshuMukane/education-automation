from flask import Flask, render_template, redirect
from config import Config

from main.logger import getLogger
from main.extensions import db, migrate

def create_app():
    app = Flask(__name__)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404_page_not_found.html"), 404
    
    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    from .routes.index import index_bp
    from .routes.auth import auth_bp
    from .routes.api import api_bp
    from .routes.sales import sales_bp
    from .routes.teacher import teacher_bp
    from .routes.admin import admin_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)

    # Register CLI commands
    from . import commands
    commands.init_app(app)

    # Log application startup
    getLogger("event").info("Flask app initialized.")

    return app
