"""
SQLite → PostgreSQL data migration script for Benjo Moments Photography System.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Requirements:
    - DATABASE_URL set to target Postgres (in .env or environment)
    - SQLite database.db present at DATABASE_PATH (default: ./database.db)
    - Run `alembic upgrade head` on the target Postgres DB first

This script is idempotent where possible:
    - users:            skips if email already exists
    - website_settings: skips if row already exists (keeps existing)
    - all others:       inserts all rows; run once on a clean DB
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add parent dir to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import config  # noqa: E402
from db import engine, SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Asset, ContactMessage, Customer, Expense, GalleryImage,
    HeroImage, Income, Invoice, PricingPackage, User, WebsiteSettings,
)
from sqlalchemy import select, text  # noqa: E402

SQLITE_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "database.db"))


def get_sqlite(path):
    if not os.path.exists(path):
        print(f"[ERROR] SQLite database not found at: {path}")
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_users(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM users").fetchall()
    inserted = 0
    for r in rows:
        exists = session.scalar(select(User).where(User.email == r["email"]))
        if not exists:
            session.add(User(
                id=r["id"],
                name=r["name"],
                email=r["email"],
                password_hash=r["password_hash"],
                role=r["role"] or "admin",
            ))
            inserted += 1
    session.commit()
    print(f"  users: {len(rows)} read, {inserted} inserted")


def migrate_income(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM income").fetchall()
    for r in rows:
        session.add(Income(
            id=r["id"], date=r["date"], description=r["description"],
            category=r["category"], amount=r["amount"],
        ))
    session.commit()
    print(f"  income: {len(rows)} inserted")


def migrate_expenses(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM expenses").fetchall()
    for r in rows:
        session.add(Expense(
            id=r["id"], date=r["date"], description=r["description"],
            category=r["category"], amount=r["amount"],
        ))
    session.commit()
    print(f"  expenses: {len(rows)} inserted")


def migrate_customers(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM customers").fetchall()
    for r in rows:
        session.add(Customer(
            id=r["id"], name=r["name"], service=r["service"],
            amount_paid=r["amount_paid"] or 0, total_amount=r["total_amount"],
            contact=r["contact"],
        ))
    session.commit()
    print(f"  customers: {len(rows)} inserted")


def migrate_invoices(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM invoices").fetchall()
    for r in rows:
        session.add(Invoice(
            id=r["id"], invoice_number=r["invoice_number"],
            customer_id=r["customer_id"], date=r["date"],
            amount=r["amount"], status=r["status"] or "Pending",
        ))
    session.commit()
    print(f"  invoices: {len(rows)} inserted")


def migrate_assets(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM assets").fetchall()
    for r in rows:
        session.add(Asset(
            id=r["id"], name=r["name"], category=r["category"],
            value=r["value"], supplier=r["supplier"],
        ))
    session.commit()
    print(f"  assets: {len(rows)} inserted")


def migrate_gallery(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM gallery").fetchall()
    for r in rows:
        session.add(GalleryImage(
            id=r["id"], filename=r["filename"], album=r["album"],
            caption=r["caption"], published=bool(r["published"]),
        ))
    session.commit()
    print(f"  gallery: {len(rows)} inserted")


def migrate_website_settings(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM website_settings").fetchall()
    existing = session.scalar(select(WebsiteSettings))
    if existing:
        print(f"  website_settings: row already exists — skipping")
        return
    for r in rows:
        session.add(WebsiteSettings(
            site_name=r["site_name"], hero_text=r["hero_text"],
            hero_subtext=r["hero_subtext"], about_text=r["about_text"],
            contact_phone=r["contact_phone"], contact_email=r["contact_email"],
            address=r["address"],
        ))
    session.commit()
    print(f"  website_settings: {len(rows)} inserted")


def migrate_hero_images(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM hero_images").fetchall()
    for r in rows:
        session.add(HeroImage(
            id=r["id"], filename=r["filename"], display_order=r["display_order"] or 0,
        ))
    session.commit()
    print(f"  hero_images: {len(rows)} inserted")


def migrate_contact_messages(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM contact_messages").fetchall()
    for r in rows:
        session.add(ContactMessage(
            id=r["id"], name=r["name"], email=r["email"],
            phone=r["phone"], service=r["service"],
            message=r["message"], is_read=bool(r["is_read"]),
        ))
    session.commit()
    print(f"  contact_messages: {len(rows)} inserted")


def migrate_pricing_packages(sqlite_conn, session):
    rows = sqlite_conn.execute("SELECT * FROM pricing_packages").fetchall()
    for r in rows:
        session.add(PricingPackage(
            id=r["id"], name=r["name"], description=r["description"],
            price=r["price"], price_label=r["price_label"] or "/session",
            icon=r["icon"] or "fa-camera", features=r["features"],
            is_featured=bool(r["is_featured"]), display_order=r["display_order"] or 0,
            is_active=bool(r["is_active"]) if r["is_active"] is not None else True,
        ))
    session.commit()
    print(f"  pricing_packages: {len(rows)} inserted")


def reset_sequences(session):
    """Reset Postgres sequences after inserting rows with explicit IDs."""
    if "sqlite" in config.DATABASE_URL:
        return
    tables = [
        "users", "income", "expenses", "customers", "invoices", "assets",
        "gallery", "website_settings", "hero_images", "contact_messages",
        "pricing_packages",
    ]
    for table in tables:
        session.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"
        ))
    session.commit()
    print("  sequences reset for all tables")


if __name__ == "__main__":
    print(f"\nBenjo Moments — SQLite → PostgreSQL Migration")
    print(f"  Source SQLite: {SQLITE_PATH}")
    print(f"  Target DB:     {config.DATABASE_URL}\n")

    sqlite_conn = get_sqlite(SQLITE_PATH)
    with SessionLocal() as session:
        try:
            migrate_users(sqlite_conn, session)
            migrate_website_settings(sqlite_conn, session)
            migrate_hero_images(sqlite_conn, session)
            migrate_pricing_packages(sqlite_conn, session)
            migrate_income(sqlite_conn, session)
            migrate_expenses(sqlite_conn, session)
            migrate_assets(sqlite_conn, session)
            migrate_customers(sqlite_conn, session)
            migrate_invoices(sqlite_conn, session)
            migrate_gallery(sqlite_conn, session)
            migrate_contact_messages(sqlite_conn, session)
            reset_sequences(session)
            print("\n✅  Migration complete.")
        except Exception as exc:
            session.rollback()
            print(f"\n❌  Migration failed: {exc}")
            raise
    sqlite_conn.close()
