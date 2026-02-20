"""
SQLAlchemy-based CRUD operations for Benjo Moments Photography System.

This module is a drop-in replacement for database.py.
All functions have the same signatures as the sqlite3 originals so that
admin.py, public.py, and auth.py require zero changes.

Results are returned as plain dicts (or lists of dicts) that support
both dict-key access  row['field']  and attribute access  row.field
via the _Row namedtuple wrapper, keeping full backwards compatibility
with templates that use either style.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

import config
from db import SessionLocal
from models import (
    Asset, AuditLog, ContactMessage, Customer, Expense, GalleryImage,
    HeroImage, Income, Invoice, PricingPackage, User, WebsiteSettings,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row compatibility wrapper
# ---------------------------------------------------------------------------
class _Row(dict):
    """Dict subclass that supports attribute-style access, like sqlite3.Row."""
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value


def _to_row(obj) -> Optional[_Row]:
    if obj is None:
        return None
    return _Row(obj.as_dict())


def _to_rows(objs) -> list[_Row]:
    return [_to_row(o) for o in objs]


# ---------------------------------------------------------------------------
# Seed / init helpers (called from app.py on startup)
# ---------------------------------------------------------------------------
def init_db():
    """No-op: tables are created by Alembic migrations."""
    pass


def create_default_admin():
    """Create a seeded admin user if TEST_AUTH_MODE is off and no users exist."""
    if not config.DEFAULT_ADMIN_PASSWORD:
        return
    with SessionLocal() as session:
        exists = session.scalar(select(func.count()).select_from(User))
        if exists == 0:
            session.add(User(
                name=config.DEFAULT_ADMIN_NAME,
                email=config.DEFAULT_ADMIN_EMAIL,
                password_hash=generate_password_hash(config.DEFAULT_ADMIN_PASSWORD),
                role="admin",
            ))
            session.commit()
            logger.info("Default admin user created: %s", config.DEFAULT_ADMIN_EMAIL)


def init_default_settings():
    """Seed a website_settings row if none exists."""
    with SessionLocal() as session:
        exists = session.scalar(select(func.count()).select_from(WebsiteSettings))
        if exists == 0:
            session.add(WebsiteSettings(
                site_name="Benjo Moments",
                hero_text="Capturing Your Precious Moments",
                hero_subtext="Professional Photography for Weddings, Events & Portraits",
                about_text=(
                    "Benjo Moments is a professional photography studio dedicated to capturing "
                    "life's most precious moments. With years of experience in wedding, portrait, "
                    "and event photography, we bring creativity and passion to every shoot."
                ),
                contact_phone="0759989861 / 0778728089",
                contact_email="info@benjomoments.com",
                address="Carol House, Plot 40, next to Bible House, along Bombo Road, Wandegeya",
            ))
            session.commit()
            logger.info("Default website settings seeded.")


def create_default_pricing_packages():
    """Seed default pricing packages if none exist."""
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(PricingPackage))
        if count == 0:
            defaults = [
                PricingPackage(
                    name="Basic",
                    description="Perfect for portraits & small events",
                    price=300000,
                    price_label="/session",
                    icon="fa-camera",
                    features="2 Hours Coverage|50+ Edited Photos|Digital Download|1 Location|Basic Retouching",
                    is_featured=False,
                    display_order=1,
                ),
                PricingPackage(
                    name="Premium",
                    description="Best for weddings & kukyala",
                    price=1500000,
                    price_label="/event",
                    icon="fa-heart",
                    features="Full Day Coverage|300+ Edited Photos|Photo Album Included|Multiple Locations|2 Photographers|Premium Retouching",
                    is_featured=True,
                    display_order=2,
                ),
                PricingPackage(
                    name="Full Package",
                    description="Photo + Video combo deal",
                    price=2500000,
                    price_label="/event",
                    icon="fa-video",
                    features="Photography + Videography|500+ Photos & Full Video|Highlight Reel|Premium Album + USB|Same Day Edit Preview|Drone Coverage",
                    is_featured=False,
                    display_order=3,
                ),
            ]
            session.add_all(defaults)
            session.commit()
            logger.info("Default pricing packages seeded.")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def get_user_by_email(email: str) -> Optional[_Row]:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            return None
        row = _Row(user.as_dict())
        row["password_hash"] = user.password_hash  # needed for auth check
        return row


def get_user_by_id(user_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        row = _Row(user.as_dict())
        row["password_hash"] = user.password_hash
        return row


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------
def get_all_income() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Income).where(Income.is_deleted == False).order_by(Income.date.desc())  # noqa: E712
        ).all()
        return _to_rows(rows)


def add_income(date, description, category, amount) -> None:
    with SessionLocal() as session:
        session.add(Income(date=date, description=description, category=category, amount=amount))
        session.commit()


def delete_income(income_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Income, income_id)
        if row:
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()


def get_total_income() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Income.amount), 0)).where(Income.is_deleted == False)  # noqa: E712
        )
        return float(total)


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------
def get_all_expenses() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Expense).where(Expense.is_deleted == False).order_by(Expense.date.desc())  # noqa: E712
        ).all()
        return _to_rows(rows)


def add_expense(date, description, category, amount) -> None:
    with SessionLocal() as session:
        session.add(Expense(date=date, description=description, category=category, amount=amount))
        session.commit()


def delete_expense(expense_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Expense, expense_id)
        if row:
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()


def get_total_expenses() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.is_deleted == False)  # noqa: E712
        )
        return float(total)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def get_all_customers() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Customer).where(Customer.is_deleted == False).order_by(Customer.created_at.desc())  # noqa: E712
        ).all()
        return _to_rows(rows)


def get_customer(customer_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.scalar(
            select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)  # noqa: E712
        )
        return _to_row(row)


def add_customer(name, service, amount_paid, total_amount, contact) -> None:
    with SessionLocal() as session:
        session.add(Customer(
            name=name, service=service, amount_paid=amount_paid,
            total_amount=total_amount, contact=contact,
        ))
        session.commit()


def update_customer_payment(customer_id: int, amount_paid) -> None:
    with SessionLocal() as session:
        row = session.get(Customer, customer_id)
        if row:
            row.amount_paid = amount_paid
            session.commit()


def delete_customer(customer_id: int) -> None:
    """Soft-delete customer and their invoices."""
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if customer:
            for inv in customer.invoices:
                inv.is_deleted = True
                inv.deleted_at = datetime.utcnow()
            customer.is_deleted = True
            customer.deleted_at = datetime.utcnow()
            session.commit()


def get_total_pending_balance() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(
                func.coalesce(
                    func.sum(Customer.total_amount - Customer.amount_paid), 0
                )
            ).where(Customer.is_deleted == False)  # noqa: E712
        )
        return float(total)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------
def get_all_invoices() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Invoice)
            .where(Invoice.is_deleted == False)  # noqa: E712
            .join(Customer, Invoice.customer_id == Customer.id)
            .order_by(Invoice.date.desc())
        ).all()
        # Eagerly build rows including customer_name
        result = []
        for inv in rows:
            d = inv.as_dict()
            d["customer_name"] = inv.customer.name if inv.customer else ""
            result.append(_Row(d))
        return result


def _gen_invoice_number(session) -> str:
    for _ in range(20):
        candidate = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
        exists = session.scalar(
            select(Invoice).where(Invoice.invoice_number == candidate)
        )
        if not exists:
            return candidate
    raise RuntimeError("Unable to generate unique invoice number.")


def generate_invoice_number() -> str:
    with SessionLocal() as session:
        return _gen_invoice_number(session)


def add_invoice(invoice_number, customer_id, date, amount) -> str:
    with SessionLocal() as session:
        for attempt in range(20):
            num = (invoice_number or "").strip() or _gen_invoice_number(session)
            try:
                inv = Invoice(invoice_number=num, customer_id=customer_id, date=date, amount=amount)
                session.add(inv)
                session.commit()
                return num
            except IntegrityError:
                session.rollback()
                if invoice_number:
                    raise ValueError("Invoice number already exists. Use a different number.")
        raise RuntimeError("Unable to create invoice due to repeated invoice number conflicts.")


def update_invoice_status(invoice_id: int, status: str) -> None:
    with SessionLocal() as session:
        row = session.get(Invoice, invoice_id)
        if row:
            row.status = status
            session.commit()


def delete_invoice(invoice_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Invoice, invoice_id)
        if row:
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def get_all_assets() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Asset).order_by(Asset.created_at.desc())
        ).all()
        return _to_rows(rows)


def add_asset(name, category, value, supplier) -> None:
    with SessionLocal() as session:
        session.add(Asset(name=name, category=category, value=value, supplier=supplier))
        session.commit()


def delete_asset(asset_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(Asset, asset_id)
        if row:
            session.delete(row)
            session.commit()


def get_total_asset_value() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Asset.value), 0))
        )
        return float(total)


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------
def get_all_gallery_images() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(GalleryImage)
            .where(GalleryImage.is_deleted == False)  # noqa: E712
            .order_by(GalleryImage.uploaded_at.desc())
        ).all()
        return _to_rows(rows)


def get_published_gallery_images(album=None) -> list[_Row]:
    with SessionLocal() as session:
        q = select(GalleryImage).where(
            GalleryImage.published == True,  # noqa: E712
            GalleryImage.is_deleted == False,  # noqa: E712
        )
        if album:
            q = q.where(GalleryImage.album == album)
        rows = session.scalars(q.order_by(GalleryImage.uploaded_at.desc())).all()
        return _to_rows(rows)


def add_gallery_image(filename, album, caption) -> None:
    with SessionLocal() as session:
        session.add(GalleryImage(filename=filename, album=album, caption=caption, published=True))
        session.commit()


def toggle_gallery_publish(image_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(GalleryImage, image_id)
        if row:
            row.published = not row.published
            session.commit()


def delete_gallery_image(image_id: int) -> Optional[_Row]:
    """Soft-delete the gallery DB record; return filename/album for file deletion."""
    with SessionLocal() as session:
        row = session.get(GalleryImage, image_id)
        if row:
            result = _Row({"filename": row.filename, "album": row.album})
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()
            return result
        return None


# ---------------------------------------------------------------------------
# Website Settings
# ---------------------------------------------------------------------------
def get_website_settings() -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.scalar(select(WebsiteSettings).limit(1))
        return _to_row(row)


def update_website_settings(site_name, hero_text, hero_subtext, about_text,
                             contact_phone, contact_email, address) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(WebsiteSettings).limit(1))
        if row:
            row.site_name = site_name
            row.hero_text = hero_text
            row.hero_subtext = hero_subtext
            row.about_text = about_text
            row.contact_phone = contact_phone
            row.contact_email = contact_email
            row.address = address
            row.updated_at = datetime.utcnow()
        else:
            session.add(WebsiteSettings(
                site_name=site_name, hero_text=hero_text, hero_subtext=hero_subtext,
                about_text=about_text, contact_phone=contact_phone,
                contact_email=contact_email, address=address,
            ))
        session.commit()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def get_income_by_date_range(start_date, end_date) -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Income)
            .where(Income.is_deleted == False, Income.date.between(start_date, end_date))  # noqa: E712
            .order_by(Income.date.desc())
        ).all()
        return _to_rows(rows)


def get_expenses_by_date_range(start_date, end_date) -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Expense)
            .where(Expense.is_deleted == False, Expense.date.between(start_date, end_date))  # noqa: E712
            .order_by(Expense.date.desc())
        ).all()
        return _to_rows(rows)


def get_recent_transactions(limit: int = 10) -> list[_Row]:
    """Return recent income + expense combined, sorted by date, limited."""
    with SessionLocal() as session:
        income_rows = session.scalars(
            select(Income).where(Income.is_deleted == False).order_by(Income.date.desc()).limit(limit)  # noqa: E712
        ).all()
        expense_rows = session.scalars(
            select(Expense).where(Expense.is_deleted == False).order_by(Expense.date.desc()).limit(limit)  # noqa: E712
        ).all()

    transactions = []
    for r in income_rows:
        d = r.as_dict()
        d["type"] = "income"
        transactions.append(_Row(d))
    for r in expense_rows:
        d = r.as_dict()
        d["type"] = "expense"
        transactions.append(_Row(d))

    transactions.sort(key=lambda x: x["date"] or datetime.min.date(), reverse=True)
    return transactions[:limit]


# ---------------------------------------------------------------------------
# Contact Messages
# ---------------------------------------------------------------------------
def get_all_messages() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(ContactMessage).order_by(ContactMessage.created_at.desc())
        ).all()
        return _to_rows(rows)


def get_unread_messages_count() -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count()).select_from(ContactMessage).where(ContactMessage.is_read == False)  # noqa: E712
        )


def add_contact_message(name, email, phone, service, message) -> None:
    with SessionLocal() as session:
        session.add(ContactMessage(
            name=name, email=email, phone=phone, service=service, message=message
        ))
        session.commit()


def mark_message_read(message_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(ContactMessage, message_id)
        if row:
            row.is_read = True
            session.commit()


def delete_message(message_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(ContactMessage, message_id)
        if row:
            session.delete(row)
            session.commit()


# ---------------------------------------------------------------------------
# Pricing Packages
# ---------------------------------------------------------------------------
def get_all_pricing_packages() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(PricingPackage).order_by(PricingPackage.display_order, PricingPackage.id)
        ).all()
        return _to_rows(rows)


def get_active_pricing_packages() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(PricingPackage)
            .where(PricingPackage.is_active == True)  # noqa: E712
            .order_by(PricingPackage.display_order, PricingPackage.id)
        ).all()
        return _to_rows(rows)


def get_pricing_package(package_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        return _to_row(row)


def add_pricing_package(name, description, price, price_label, icon, features,
                         is_featured, display_order) -> None:
    with SessionLocal() as session:
        session.add(PricingPackage(
            name=name, description=description, price=price, price_label=price_label,
            icon=icon, features=features, is_featured=bool(is_featured),
            display_order=display_order,
        ))
        session.commit()


def update_pricing_package(package_id, name, description, price, price_label, icon,
                            features, is_featured, display_order) -> None:
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            row.name = name
            row.description = description
            row.price = price
            row.price_label = price_label
            row.icon = icon
            row.features = features
            row.is_featured = bool(is_featured)
            row.display_order = display_order
            session.commit()


def delete_pricing_package(package_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            session.delete(row)
            session.commit()


def toggle_pricing_package(package_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            row.is_active = not row.is_active
            session.commit()


# ---------------------------------------------------------------------------
# Hero Images
# ---------------------------------------------------------------------------
def get_all_hero_images() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(HeroImage).order_by(HeroImage.display_order, HeroImage.id)
        ).all()
        return _to_rows(rows)


def add_hero_image(filename, display_order) -> None:
    with SessionLocal() as session:
        session.add(HeroImage(filename=filename, display_order=display_order))
        session.commit()


def delete_hero_image(image_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.get(HeroImage, image_id)
        if row:
            result = _Row({"filename": row.filename})
            session.delete(row)
            session.commit()
            return result
        return None


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------
def log_audit(user_email: str, action: str, entity_type: str = None,
               entity_id: int = None, details: str = None) -> None:
    """Write an audit log entry. Swallows errors to never break the main flow."""
    try:
        with SessionLocal() as session:
            session.add(AuditLog(
                user_email=user_email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details_json=details,
            ))
            session.commit()
    except Exception as exc:
        logger.warning("Audit log failed (non-fatal): %s", exc)


def get_recent_audit_logs(limit: int = 100) -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        ).all()
        return [_Row(r.as_dict()) for r in rows]
