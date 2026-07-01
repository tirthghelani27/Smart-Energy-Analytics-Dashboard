#!/usr/bin/env python3
"""
database/check_db.py
====================
Run this to verify MySQL is connected and all tables exist.

Usage:
    python database/check_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from src.extensions import db

REQUIRED_TABLES = [
    'users', 'electricity_usage', 'appliances', 'predictions',
    'alerts', 'recommendations', 'carbon_footprint', 'reports',
]

def check():
    app = create_app()
    with app.app_context():
        print(f"\n{'='*50}")
        print("Smart Energy Analytics — Database Check")
        print(f"{'='*50}")
        
        # Check connection
        try:
            with db.engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                print(f"\n✓ MySQL connection: OK")
                print(f"  URI: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1]}")
        except Exception as e:
            print(f"\n✗ MySQL connection FAILED: {e}")
            print("\nFix: Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME in your .env file")
            sys.exit(1)
        
        # Check tables
        print(f"\nTable check:")
        inspector = db.inspect(db.engine)
        existing = inspector.get_table_names()
        
        all_ok = True
        for table in REQUIRED_TABLES:
            if table in existing:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table}  ← MISSING")
                all_ok = False
        
        if not all_ok:
            print(f"\n{'='*50}")
            print("PROBLEM: Missing tables found!")
            print("\nRun these commands to create them:")
            print("  mysql -u root -p smart_energy_db < database/schema.sql")
            print("\nThen optionally load sample data:")
            print("  mysql -u root -p smart_energy_db < database/seed_sample_data.sql")
            print("  python database/set_sample_passwords.py")
            sys.exit(1)
        else:
            # Count rows in users
            try:
                with db.engine.connect() as conn:
                    from sqlalchemy import text
                    r = conn.execute(text("SELECT COUNT(*) FROM users"))
                    count = r.scalar()
                print(f"\n✓ All {len(REQUIRED_TABLES)} tables exist")
                print(f"  Users in database: {count}")
                print(f"\n✓ Database is ready. You can register and log in.")
            except Exception as e:
                print(f"  Warning: {e}")

if __name__ == '__main__':
    check()
