# ============================================================
# src/extensions.py
#
# Single source of truth for every Flask extension object.
#
# WHY THIS FILE EXISTS
# --------------------
# Flask's application factory pattern requires that extension
# objects (db, bcrypt, mail, etc.) be created ONCE, at module
# level, with NO Flask app bound to them yet.  They are later
# wired to the real app inside create_app() via init_app().
#
# The problem with storing these in app.py
# -----------------------------------------
# When any model does:
#
#     from app import db
#
# Python must import the entire app.py module.  app.py imports
# config.py (which calls load_dotenv()), then defines db, then
# defines create_app.  This works, BUT it creates a tight
# coupling: models → app.py → config.py → everything.
#
# More importantly, if anything in the import chain triggers
# create_app() a second time, or if the Flask CLI and the
# application disagree about which `app` object is "current",
# SQLAlchemy raises:
#
#     RuntimeError: The current Flask app is not registered
#     with this 'SQLAlchemy' instance.
#
# The fix
# --------
# Move all extension objects here.  Models and services import
# from src.extensions, NOT from app.  app.py imports from here
# too, so there is still exactly ONE SQLAlchemy() instance —
# it just lives in a module that has no circular dependencies.
# ============================================================

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_migrate import Migrate

db           = SQLAlchemy()
login_manager = LoginManager()
bcrypt        = Bcrypt()
mail          = Mail()
migrate       = Migrate()
