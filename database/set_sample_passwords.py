"""
Set Sample Passwords
=====================
The seed_sample_data.sql file inserts placeholder password hashes for
the demo accounts (admin / demo_user) because bcrypt hashes cannot be
hand-written in SQL — they must be generated using the app's own
Flask-Bcrypt instance.

Run this script ONCE after loading schema.sql and seed_sample_data.sql
to set real, working passwords for the seeded accounts.

Usage:
    cd smart_energy
    python database/set_sample_passwords.py

This sets:
    admin      / Admin@123
    demo_user  / User@123
"""
import os
import sys

# Allow running this script from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db          # noqa: E402
from src.models.user import User        # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        demo = User.query.filter_by(username="demo_user").first()

        if not admin or not demo:
            print("ERROR: Seeded users not found. Run seed_sample_data.sql first.")
            sys.exit(1)

        admin.set_password("Admin@123")
        demo.set_password("User@123")
        db.session.commit()

        print("Passwords set successfully:")
        print("  admin     / Admin@123")
        print("  demo_user / User@123")


if __name__ == "__main__":
    main()
