"""
PostgreSQL CRUD operations for Benjo Moments Photography System.

Phase 6 additions:
  - _actor_email(), _client_ip(), _user_agent() — safe request-context helpers
  - _validate_amount(), _validate_date() — server-side input validators
  - log_audit() calls on every mutating function
  - restore_* functions for soft-deleted entities
"""
from __future__ import annotations

import json
import logging
import math
import secrets
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

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
    """Dictionary row with optional attribute-style access."""
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
# Request-context helpers  (Phase 6)
# ---------------------------------------------------------------------------
def _actor_email() -> str:
    """Return the logged-in user's email, or 'system' outside a request."""
    try:
        from flask import has_request_context, session
        if has_request_context():
            return session.get("user_email", "unknown")
    except Exception:
        pass
    return "system"


def _client_ip() -> str:
    """Return the client IP address, or empty string outside a request."""
    try:
        from flask import has_request_context, request
        if has_request_context():
            return request.remote_addr or ""
    except Exception:
        pass
    return ""


def _user_agent() -> str:
    """Return the User-Agent header, truncated to 200 chars."""
    try:
        from flask import has_request_context, request
        if has_request_context():
            ua = request.headers.get("User-Agent", "")
            return ua[:200]
    except Exception:
        pass
    return ""


def _audit_details(**kwargs) -> str:
    """Serialize extra audit context to a JSON string."""
    payload = {k: v for k, v in kwargs.items() if v is not None and v != ""}
    payload.update({"ip": _client_ip(), "ua": _user_agent()})
    return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Input validators  (Phase 6/7)
# ---------------------------------------------------------------------------
def _validate_amount(value, label: str = "Amount") -> float:
    """Parse and validate a monetary amount. Raises ValueError on bad input."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(amount):
        raise ValueError(f"{label} must be a finite number.")
    if amount < 0:
        raise ValueError(f"{label} must be zero or greater.")
    return amount


def _validate_positive_amount(value, label: str = "Amount") -> float:
    amount = _validate_amount(value, label)
    if amount <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return amount


def _validate_date(value, label: str = "Date"):
    """Parse and validate a date. Accepts date objects or 'YYYY-MM-DD' strings."""
    if isinstance(value, (date_type, datetime)):
        return value if isinstance(value, date_type) else value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a valid date in YYYY-MM-DD format.")


# ---------------------------------------------------------------------------
# Seed / init helpers (called from app.py on startup)
# ---------------------------------------------------------------------------
def init_db():
    """No-op: tables are created by Alembic migrations."""
    pass


def synchronize_environment_admin():
    """Make environment credentials the single authoritative admin login."""
    if not config.DEFAULT_ADMIN_PASSWORD:
        raise RuntimeError("DEFAULT_ADMIN_PASSWORD is required to synchronize the admin.")

    configured_email = config.DEFAULT_ADMIN_EMAIL
    with SessionLocal() as session:
        users = session.scalars(select(User).order_by(User.id).with_for_update()).all()
        configured_user = next(
            (user for user in users if user.email.strip().lower() == configured_email),
            None,
        )

        if configured_user is None:
            configured_user = User(
                name=config.DEFAULT_ADMIN_NAME,
                email=configured_email,
                password_hash=generate_password_hash(config.DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            session.add(configured_user)
        else:
            configured_user.name = config.DEFAULT_ADMIN_NAME
            configured_user.email = configured_email
            configured_user.role = "admin"
            if not check_password_hash(
                configured_user.password_hash,
                config.DEFAULT_ADMIN_PASSWORD,
            ):
                configured_user.password_hash = generate_password_hash(
                    config.DEFAULT_ADMIN_PASSWORD
                )

        removed = 0
        for user in users:
            if user is not configured_user:
                session.delete(user)
                removed += 1

        session.commit()
        logger.info(
            "Environment-managed admin synchronized: %s | removed_accounts=%s",
            configured_email,
            removed,
        )


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
                whatsapp_number="256759989861",
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
                    price=300000, price_label="/session", icon="fa-camera",
                    features="2 Hours Coverage|50+ Edited Photos|Digital Download|1 Location|Basic Retouching",
                    is_featured=False, display_order=1,
                ),
                PricingPackage(
                    name="Premium",
                    description="Best for weddings & kukyala",
                    price=1500000, price_label="/event", icon="fa-heart",
                    features="Full Day Coverage|300+ Edited Photos|Photo Album Included|Multiple Locations|2 Photographers|Premium Retouching",
                    is_featured=True, display_order=2,
                ),
                PricingPackage(
                    name="Full Package",
                    description="Photo + Video combo deal",
                    price=2500000, price_label="/event", icon="fa-video",
                    features="Photography + Videography|500+ Photos & Full Video|Highlight Reel|Premium Album + USB|Same Day Edit Preview|Drone Coverage",
                    is_featured=False, display_order=3,
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
        user = session.scalar(
            select(User).where(func.lower(User.email) == str(email).strip().lower())
        )
        if user is None:
            return None
        row = _Row(user.as_dict())
        row["password_hash"] = user.password_hash
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
    amount = _validate_positive_amount(amount, "Income amount")
    date = _validate_date(date, "Income date")
    if not str(description).strip():
        raise ValueError("Description is required.")
    if not str(category).strip():
        raise ValueError("Category is required.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = Income(date=date, description=description, category=category, amount=amount)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "income", row.id,
                  _audit_details(description=description, category=category, amount=amount))


def update_income(income_id: int, date, description, category, amount) -> None:
    amount = _validate_positive_amount(amount, "Income amount")
    date = _validate_date(date, "Income date")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Income, income_id)
        if row and not row.is_deleted:
            if row.source_invoice_id:
                raise ValueError("Invoice-generated income must be managed from the invoice.")
            row.date = date
            row.description = str(description).strip()
            row.category = str(category).strip()
            row.amount = amount
            session.commit()
            log_audit(actor, "update", "income", income_id,
                      _audit_details(description=description, category=category, amount=amount))


def delete_income(income_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Income, income_id)
        if row:
            if row.source_invoice_id:
                raise ValueError("Invoice-generated income must be managed from the invoice.")
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()
            log_audit(actor, "delete", "income", income_id,
                      _audit_details(deleted_by=actor, description=row.description))


def restore_income(income_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Income, income_id)
        if row and row.is_deleted:
            row.is_deleted = False
            row.deleted_at = None
            session.commit()
            log_audit(actor, "restore", "income", income_id, _audit_details())


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
    amount = _validate_positive_amount(amount, "Expense amount")
    date = _validate_date(date, "Expense date")
    if not str(description).strip():
        raise ValueError("Description is required.")
    if not str(category).strip():
        raise ValueError("Category is required.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = Expense(date=date, description=description, category=category, amount=amount)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "expense", row.id,
                  _audit_details(description=description, category=category, amount=amount))


def update_expense(expense_id: int, date, description, category, amount) -> None:
    amount = _validate_positive_amount(amount, "Expense amount")
    date = _validate_date(date, "Expense date")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Expense, expense_id)
        if row and not row.is_deleted:
            row.date = date
            row.description = str(description).strip()
            row.category = str(category).strip()
            row.amount = amount
            session.commit()
            log_audit(actor, "update", "expense", expense_id,
                      _audit_details(description=description, category=category, amount=amount))


def delete_expense(expense_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Expense, expense_id)
        if row:
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()
            log_audit(actor, "delete", "expense", expense_id,
                      _audit_details(deleted_by=actor, description=row.description))


def restore_expense(expense_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Expense, expense_id)
        if row and row.is_deleted:
            row.is_deleted = False
            row.deleted_at = None
            session.commit()
            log_audit(actor, "restore", "expense", expense_id, _audit_details())


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
    if not str(name).strip():
        raise ValueError("Customer name is required.")
    if not str(service).strip():
        raise ValueError("Service is required.")
    total_amount = _validate_positive_amount(total_amount, "Total amount")
    amount_paid = _validate_amount(amount_paid, "Amount paid")
    if amount_paid > total_amount:
        raise ValueError("Amount paid cannot exceed total amount.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = Customer(name=name, service=service, amount_paid=amount_paid,
                       total_amount=total_amount, contact=contact)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "customer", row.id,
                  _audit_details(name=name, service=service, total_amount=total_amount))


def update_customer_payment(customer_id: int, amount_paid) -> None:
    amount_paid = _validate_amount(amount_paid, "Amount paid")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Customer, customer_id)
        if row:
            if amount_paid > float(row.total_amount):
                raise ValueError("Amount paid cannot exceed total amount.")
            row.amount_paid = amount_paid
            session.commit()
            log_audit(actor, "update", "customer", customer_id,
                      _audit_details(amount_paid=amount_paid))


def update_customer(customer_id: int, name, service, amount_paid, total_amount, contact) -> None:
    total_amount = _validate_positive_amount(total_amount, "Total amount")
    amount_paid = _validate_amount(amount_paid, "Amount paid")
    if amount_paid > total_amount:
        raise ValueError("Amount paid cannot exceed total amount.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Customer, customer_id)
        if row and not row.is_deleted:
            paid_invoice_total = session.scalar(
                select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                    Invoice.customer_id == customer_id,
                    Invoice.status == "paid",
                    Invoice.is_deleted == False,  # noqa: E712
                )
            )
            if amount_paid < float(paid_invoice_total):
                raise ValueError(
                    "Amount paid cannot be lower than the total of paid invoices."
                )
            pending_invoice_total = session.scalar(
                select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                    Invoice.customer_id == customer_id,
                    Invoice.status == "pending",
                    Invoice.is_deleted == False,  # noqa: E712
                )
            )
            if total_amount - amount_paid < float(pending_invoice_total):
                raise ValueError(
                    "The new total would be lower than the customer's pending invoices."
                )
            row.name = str(name).strip()
            row.service = str(service).strip()
            row.amount_paid = amount_paid
            row.total_amount = total_amount
            row.contact = str(contact).strip()
            session.commit()
            log_audit(actor, "update", "customer", customer_id,
                      _audit_details(name=name, service=service, total_amount=total_amount))


def delete_customer(customer_id: int) -> None:
    """Soft-delete customer and their invoices."""
    actor = _actor_email()
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        if customer:
            for inv in customer.invoices:
                inv.is_deleted = True
                inv.deleted_at = datetime.utcnow()
            customer.is_deleted = True
            customer.deleted_at = datetime.utcnow()
            session.commit()
            log_audit(actor, "delete", "customer", customer_id,
                      _audit_details(deleted_by=actor, name=customer.name))


def restore_customer(customer_id: int) -> None:
    """Restore a soft-deleted customer (does NOT auto-restore invoices)."""
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Customer, customer_id)
        if row and row.is_deleted:
            row.is_deleted = False
            row.deleted_at = None
            session.commit()
            log_audit(actor, "restore", "customer", customer_id,
                      _audit_details(name=row.name))


def get_total_pending_balance() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(
                func.coalesce(func.sum(Customer.total_amount - Customer.amount_paid), 0)
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
        result = []
        for inv in rows:
            d = inv.as_dict()
            d["customer_name"] = inv.customer.name if inv.customer else ""
            result.append(_Row(d))
        return result


def _gen_invoice_number(session) -> str:
    for _ in range(20):
        candidate = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
        exists = session.scalar(select(Invoice).where(Invoice.invoice_number == candidate))
        if not exists:
            return candidate
    raise RuntimeError("Unable to generate unique invoice number.")


def generate_invoice_number() -> str:
    with SessionLocal() as session:
        return _gen_invoice_number(session)


def add_invoice(invoice_number, customer_id, date, amount) -> str:
    amount = _validate_positive_amount(amount, "Invoice amount")
    date = _validate_date(date, "Invoice date")
    actor = _actor_email()
    with SessionLocal() as session:
        customer = session.scalar(
            select(Customer)
            .where(Customer.id == customer_id, Customer.is_deleted == False)  # noqa: E712
            .with_for_update()
        )
        if not customer:
            raise ValueError("Selected customer does not exist.")
        pending_total = session.scalar(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.customer_id == customer_id,
                Invoice.status == "pending",
                Invoice.is_deleted == False,  # noqa: E712
            )
        )
        available_to_invoice = (
            float(customer.total_amount - customer.amount_paid) - float(pending_total)
        )
        if amount > available_to_invoice:
            raise ValueError(
                "Invoice amount cannot exceed the unbilled balance "
                f"({max(available_to_invoice, 0):,.0f})."
            )
        for _ in range(20):
            num = (invoice_number or "").strip() or _gen_invoice_number(session)
            try:
                inv = Invoice(invoice_number=num, customer_id=customer_id, date=date, amount=amount)
                session.add(inv)
                session.commit()
                log_audit(actor, "create", "invoice", inv.id,
                          _audit_details(invoice_number=num, amount=amount))
                return num
            except IntegrityError:
                session.rollback()
                if invoice_number:
                    raise ValueError("Invoice number already exists. Use a different number.")
    raise RuntimeError("Unable to create invoice due to repeated invoice number conflicts.")


def update_invoice_status(invoice_id: int, status: str) -> None:
    _VALID_STATUSES = {"pending", "paid", "cancelled"}
    status = str(status).strip().lower()
    if status not in _VALID_STATUSES:
        raise ValueError(f"Invalid invoice status '{status}'. Allowed: {', '.join(sorted(_VALID_STATUSES))}.")
    if status == "paid":
        mark_invoice_paid(invoice_id)
        return
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Invoice, invoice_id)
        if row:
            old_status = row.status
            row.status = status
            session.commit()
            log_audit(actor, "update", "invoice", invoice_id,
                      _audit_details(old_status=old_status, new_status=status))


def mark_invoice_paid(invoice_id: int) -> bool:
    """Atomically settle an invoice, customer balance, and income ledger."""
    actor = _actor_email()
    with SessionLocal() as session:
        invoice = session.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.is_deleted == False)  # noqa: E712
            .with_for_update()
        )
        if not invoice:
            raise ValueError("Invoice not found.")
        if invoice.status == "paid":
            return False

        customer = session.scalar(
            select(Customer)
            .where(Customer.id == invoice.customer_id, Customer.is_deleted == False)  # noqa: E712
            .with_for_update()
        )
        if not customer:
            raise ValueError("The invoice customer no longer exists.")

        outstanding = float(customer.total_amount - customer.amount_paid)
        if float(invoice.amount) > outstanding:
            raise ValueError(
                "This invoice exceeds the customer's current outstanding balance."
            )

        invoice.status = "paid"
        customer.amount_paid = float(customer.amount_paid) + float(invoice.amount)
        session.add(Income(
            date=date_type.today(),
            description=f"Payment for {invoice.invoice_number} - {customer.name}",
            category="Invoice Payment",
            amount=invoice.amount,
            source_invoice_id=invoice.id,
        ))
        session.commit()

    log_audit(
        actor,
        "settle",
        "invoice",
        invoice_id,
        _audit_details(invoice_number=invoice.invoice_number, amount=float(invoice.amount)),
    )
    return True


def delete_invoice(invoice_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Invoice, invoice_id)
        if row:
            generated_income = session.scalar(
                select(Income).where(
                    Income.source_invoice_id == invoice_id,
                    Income.is_deleted == False,  # noqa: E712
                )
            )
            if generated_income:
                generated_income.is_deleted = True
                generated_income.deleted_at = datetime.utcnow()
                customer = session.get(Customer, row.customer_id)
                if customer:
                    customer.amount_paid = max(
                        0,
                        float(customer.amount_paid) - float(row.amount),
                    )
            row.is_deleted = True
            row.deleted_at = datetime.utcnow()
            session.commit()
            log_audit(actor, "delete", "invoice", invoice_id,
                      _audit_details(deleted_by=actor, invoice_number=row.invoice_number))


def restore_invoice(invoice_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Invoice, invoice_id)
        if row and row.is_deleted:
            row.is_deleted = False
            row.deleted_at = None
            session.commit()
            log_audit(actor, "restore", "invoice", invoice_id,
                      _audit_details(invoice_number=row.invoice_number))


# ---------------------------------------------------------------------------
# Assets  (hard delete, but audited)
# ---------------------------------------------------------------------------
def get_all_assets() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(select(Asset).order_by(Asset.created_at.desc())).all()
        return _to_rows(rows)


def add_asset(name, category, value, supplier) -> None:
    if not str(name).strip():
        raise ValueError("Asset name is required.")
    value = _validate_positive_amount(value, "Asset value")
    actor = _actor_email()
    with SessionLocal() as session:
        row = Asset(name=name, category=category, value=value, supplier=supplier)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "asset", row.id,
                  _audit_details(name=name, category=category, value=value))


def update_asset(asset_id: int, name, category, value, supplier) -> None:
    value = _validate_positive_amount(value, "Asset value")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Asset, asset_id)
        if row:
            row.name = str(name).strip()
            row.category = str(category).strip()
            row.value = value
            row.supplier = str(supplier).strip()
            session.commit()
            log_audit(actor, "update", "asset", asset_id,
                      _audit_details(name=name, category=category, value=value))


def delete_asset(asset_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Asset, asset_id)
        if row:
            name = row.name
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "asset", asset_id,
                      _audit_details(deleted_by=actor, name=name))


def get_total_asset_value() -> float:
    with SessionLocal() as session:
        total = session.scalar(select(func.coalesce(func.sum(Asset.value), 0)))
        return float(total)


# ---------------------------------------------------------------------------
# Gallery  (soft delete with restore)
# ---------------------------------------------------------------------------
def get_all_gallery_images() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(GalleryImage)
            .where(GalleryImage.is_deleted == False)  # noqa: E712
            .order_by(GalleryImage.uploaded_at.desc())
        ).all()
        return _to_rows(rows)


def get_published_gallery_images(album=None, limit=None) -> list[_Row]:
    with SessionLocal() as session:
        q = select(GalleryImage).where(
            GalleryImage.published == True,  # noqa: E712
            GalleryImage.is_deleted == False,  # noqa: E712
        )
        if album:
            q = q.where(GalleryImage.album == album)
        q = q.order_by(GalleryImage.uploaded_at.desc())
        if limit is not None:
            q = q.limit(max(0, int(limit)))
        rows = session.scalars(q).all()
        return _to_rows(rows)


def add_gallery_image(filename, album, caption) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = GalleryImage(filename=filename, album=album, caption=caption, published=True)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "gallery", row.id,
                  _audit_details(filename=filename, album=album))


def toggle_gallery_publish(image_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(GalleryImage, image_id)
        if row:
            row.published = not row.published
            new_state = row.published
            session.commit()
            log_audit(actor, "toggle_publish", "gallery", image_id,
                      _audit_details(published=new_state))


def delete_gallery_image(image_id: int) -> Optional[_Row]:
    """Delete the gallery record and return its file location."""
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(GalleryImage, image_id)
        if row:
            result = _Row({"filename": row.filename, "album": row.album})
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "gallery", image_id,
                      _audit_details(deleted_by=actor, filename=row.filename, album=row.album))
            return result
        return None


def restore_gallery_image(image_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(GalleryImage, image_id)
        if row and row.is_deleted:
            row.is_deleted = False
            row.deleted_at = None
            session.commit()
            log_audit(actor, "restore", "gallery", image_id,
                      _audit_details(filename=row.filename))


# ---------------------------------------------------------------------------
# Website Settings
# ---------------------------------------------------------------------------
def get_website_settings() -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.scalar(select(WebsiteSettings).limit(1))
        return _to_row(row)


def update_website_settings(
    site_name,
    hero_text,
    hero_subtext,
    about_text,
    contact_phone,
    contact_email,
    address,
    facebook_url,
    instagram_url,
    youtube_url,
    whatsapp_number,
) -> None:
    actor = _actor_email()
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
            row.facebook_url = facebook_url
            row.instagram_url = instagram_url
            row.youtube_url = youtube_url
            row.whatsapp_number = whatsapp_number
            row.updated_at = datetime.utcnow()
            row_id = row.id
        else:
            new_row = WebsiteSettings(
                site_name=site_name, hero_text=hero_text, hero_subtext=hero_subtext,
                about_text=about_text, contact_phone=contact_phone,
                contact_email=contact_email, address=address,
                facebook_url=facebook_url, instagram_url=instagram_url,
                youtube_url=youtube_url, whatsapp_number=whatsapp_number,
            )
            session.add(new_row)
            session.flush()
            row_id = new_row.id
        session.commit()
        log_audit(actor, "update", "website_settings", row_id,
                  _audit_details(site_name=site_name))


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
    """Return recent income + expense combined, sorted by date."""
    with SessionLocal() as session:
        income_rows = session.scalars(
            select(Income).where(Income.is_deleted == False).order_by(Income.date.desc()).limit(limit)  # noqa: E712
        ).all()
        expense_rows = session.scalars(
            select(Expense).where(Expense.is_deleted == False).order_by(Expense.date.desc()).limit(limit)  # noqa: E712
        ).all()

    transactions = []
    for r in income_rows:
        d = r.as_dict(); d["type"] = "income"; transactions.append(_Row(d))
    for r in expense_rows:
        d = r.as_dict(); d["type"] = "expense"; transactions.append(_Row(d))

    transactions.sort(key=lambda x: x["date"] or datetime.min.date(), reverse=True)
    return transactions[:limit]


# ---------------------------------------------------------------------------
# Contact Messages  (hard delete, but audited)
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
    actor = _actor_email()
    with SessionLocal() as session:
        row = ContactMessage(name=name, email=email, phone=phone, service=service, message=message)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "contact_message", row.id,
                  _audit_details(name=name, email=email, service=service))


def mark_message_read(message_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ContactMessage, message_id)
        if row:
            row.is_read = True
            session.commit()
            log_audit(actor, "update", "contact_message", message_id,
                      _audit_details(action="mark_read"))


def delete_message(message_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ContactMessage, message_id)
        if row:
            # Capture fields BEFORE deleting — ORM object becomes detached after commit
            captured_email = row.email
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "contact_message", message_id,
                      _audit_details(deleted_by=actor, email=captured_email))


# ---------------------------------------------------------------------------
# Pricing Packages  (hard delete, but audited)
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
    actor = _actor_email()
    with SessionLocal() as session:
        row = PricingPackage(
            name=name, description=description, price=price, price_label=price_label,
            icon=icon, features=features, is_featured=bool(is_featured),
            display_order=display_order,
        )
        session.add(row)
        session.commit()
        log_audit(actor, "create", "pricing_package", row.id,
                  _audit_details(name=name, price=price))


def update_pricing_package(package_id, name, description, price, price_label, icon,
                            features, is_featured, display_order) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            row.name = name; row.description = description; row.price = price
            row.price_label = price_label; row.icon = icon; row.features = features
            row.is_featured = bool(is_featured); row.display_order = display_order
            session.commit()
            log_audit(actor, "update", "pricing_package", package_id,
                      _audit_details(name=name, price=price))


def delete_pricing_package(package_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            name = row.name
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "pricing_package", package_id,
                      _audit_details(deleted_by=actor, name=name))


def toggle_pricing_package(package_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(PricingPackage, package_id)
        if row:
            row.is_active = not row.is_active
            new_state = row.is_active
            session.commit()
            log_audit(actor, "toggle_active", "pricing_package", package_id,
                      _audit_details(is_active=new_state))


# ---------------------------------------------------------------------------
# Hero Images  (hard delete, but audited)
# ---------------------------------------------------------------------------
def get_all_hero_images() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(HeroImage).order_by(HeroImage.display_order, HeroImage.id)
        ).all()
        return _to_rows(rows)


def add_hero_image(filename, display_order) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = HeroImage(filename=filename, display_order=display_order)
        session.add(row)
        session.commit()
        log_audit(actor, "create", "hero_image", row.id,
                  _audit_details(filename=filename))


def delete_hero_image(image_id: int) -> Optional[_Row]:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(HeroImage, image_id)
        if row:
            result = _Row({"filename": row.filename})
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "hero_image", image_id,
                      _audit_details(deleted_by=actor, filename=result["filename"]))
            return result
        return None


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------
def log_audit(user_email: str, action: str, entity_type: str = None,
               entity_id: int = None, details: str = None) -> None:
    """Write an audit log entry. Swallows ALL errors to never break the main flow."""
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
