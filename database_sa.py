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

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash, generate_password_hash

import config
from db import SessionLocal
from models import (
    Asset, AuditLog, ClientCollection, ClientCollectionImage, ContactMessage,
    Customer, Expense, GalleryComment, GalleryDownload, GalleryImage, GalleryLike,
    GalleryVisitor, HeroImage, Income, Invoice, PricingPackage,
    ProfessionalService, ServiceCategory, User, WebsiteSettings,
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


def _validate_optional_date(value, label: str):
    if value in (None, ""):
        return None
    return _validate_date(value, label)


# ---------------------------------------------------------------------------
# Seed / init helpers (called from app.py on startup)
# ---------------------------------------------------------------------------
def init_db():
    """No-op: tables are created by Alembic migrations."""
    pass


def synchronize_environment_admin():
    """Create or refresh the bootstrap admin without removing other admins."""
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
                configured_user.auth_version += 1
            configured_user.is_active = True

        session.commit()
        logger.info("Bootstrap administrator synchronized: %s", configured_email)


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
                whatsapp_number="256759189861",
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


def create_default_services():
    """Seed the editable public service catalogue once."""
    catalogue = [
        (
            "Events & Celebrations",
            "Photography for life's milestones and gatherings.",
            "fa-champagne-glasses",
            "https://images.pexels.com/photos/1024993/pexels-photo-1024993.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Weddings & Introductions (Kwanjula)", "Engagements", "Birthday Parties",
                "Baby Showers & Gender Reveals", "Graduations", "Anniversaries", "Family Reunions",
            ],
        ),
        (
            "Corporate & Business",
            "Professional imagery for organizations, teams, and properties.",
            "fa-building",
            "https://images.pexels.com/photos/7648306/pexels-photo-7648306.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Corporate Events & Conferences", "Product Launches", "Company Profiles & Branding",
                "Staff Portraits / Headshots", "Office & Workplace Photography", "Real Estate & Property",
            ],
        ),
        (
            "Religious & Community",
            "Respectful coverage of faith, remembrance, and community life.",
            "fa-people-group",
            "https://images.pexels.com/photos/8815027/pexels-photo-8815027.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Church Services & Crusades", "Baptisms", "Dedications", "Funerals & Memorials",
                "Community Outreach Programs",
            ],
        ),
        (
            "Lifestyle & Studio",
            "Personal portraits and carefully directed studio sessions.",
            "fa-camera-retro",
            "https://images.pexels.com/photos/11388583/pexels-photo-11388583.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Portrait Photography", "Maternity Shoots", "Newborn & Baby Photography",
                "Fashion & Model Portfolios", "Couple / Pre-wedding Shoots",
            ],
        ),
        (
            "Media & Creative",
            "Story-led photography and production for artists and destinations.",
            "fa-film",
            "https://images.pexels.com/photos/2608519/pexels-photo-2608519.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Music Videos & Behind-the-Scenes", "Concerts & Live Performances",
                "Documentary Photography", "Travel & Tourism", "Food Photography",
            ],
        ),
        (
            "Commercial & Marketing",
            "Campaign-ready images built to sell products and ideas.",
            "fa-bullhorn",
            "https://images.pexels.com/photos/2388569/pexels-photo-2388569.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Advertising Campaigns", "E-commerce Product Photos", "Billboards & Print Ads",
                "Social Media Content Creation",
            ],
        ),
        (
            "Additional Services",
            "Everyday production and finishing services from the Benjo Moments team.",
            "fa-wand-magic-sparkles",
            "https://images.pexels.com/photos/4348404/pexels-photo-4348404.jpeg?auto=compress&cs=tinysrgb&w=900",
            [
                "Video Production", "Graphics Design", "Photo & Video Editing", "Photo Printing",
                "Passport & ID Photos", "Custom Requests",
            ],
        ),
    ]
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(ServiceCategory)):
            return
        for category_order, (name, description, icon, image_url, services) in enumerate(catalogue, 1):
            category = ServiceCategory(
                name=name,
                description=description,
                icon=icon,
                image_url=image_url,
                display_order=category_order,
            )
            category.services = [
                ProfessionalService(name=service_name, display_order=service_order, icon="fa-camera")
                for service_order, service_name in enumerate(services, 1)
            ]
            session.add(category)
        session.commit()
        logger.info("Default professional service catalogue seeded.")


def _service_category_row(category: ServiceCategory, active_only: bool = False) -> _Row:
    row = _to_row(category)
    services = category.services
    if active_only:
        services = [service for service in services if service.is_active]
    row["services"] = _to_rows(services)
    return row


def get_service_catalogue(active_only: bool = True) -> list[_Row]:
    with SessionLocal() as session:
        query = select(ServiceCategory).options(selectinload(ServiceCategory.services))
        if active_only:
            query = query.where(ServiceCategory.is_active == True)  # noqa: E712
        categories = session.scalars(
            query.order_by(ServiceCategory.display_order, ServiceCategory.id)
        ).unique().all()
        result = []
        for category in categories:
            result.append(_service_category_row(category, active_only=active_only))
        return result


def add_service_category(name, description, icon, image_url, display_order) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = ServiceCategory(
            name=str(name).strip()[:255],
            description=str(description).strip(),
            icon=str(icon).strip()[:100] or "fa-camera",
            image_url=str(image_url).strip()[:1000],
            display_order=max(0, int(display_order or 0)),
        )
        if not row.name:
            raise ValueError("Category name is required.")
        session.add(row)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("A service category with that name already exists.") from exc
        log_audit(actor, "create", "service_category", row.id, _audit_details(name=row.name))


def update_service_category(category_id, name, description, icon, image_url, display_order, is_active) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ServiceCategory, category_id)
        if not row:
            raise ValueError("Service category not found.")
        normalized_name = str(name).strip()[:255]
        if not normalized_name:
            raise ValueError("Category name is required.")
        duplicate = session.scalar(
            select(ServiceCategory.id).where(
                func.lower(ServiceCategory.name) == normalized_name.lower(),
                ServiceCategory.id != category_id,
            )
        )
        if duplicate:
            raise ValueError("A service category with that name already exists.")
        row.name = normalized_name
        row.description = str(description).strip()
        row.icon = str(icon).strip()[:100] or "fa-camera"
        row.image_url = str(image_url).strip()[:1000]
        row.display_order = max(0, int(display_order or 0))
        row.is_active = bool(is_active)
        session.commit()
        log_audit(actor, "update", "service_category", category_id, _audit_details(name=row.name))


def delete_service_category(category_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ServiceCategory, category_id)
        if row:
            name = row.name
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "service_category", category_id, _audit_details(name=name))


def add_professional_service(category_id, name, description, icon, display_order) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        if not session.get(ServiceCategory, category_id):
            raise ValueError("Service category not found.")
        row = ProfessionalService(
            category_id=category_id,
            name=str(name).strip()[:255],
            description=str(description).strip(),
            icon=str(icon).strip()[:100] or "fa-camera",
            display_order=max(0, int(display_order or 0)),
        )
        if not row.name:
            raise ValueError("Service name is required.")
        session.add(row)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("That service already exists in this category.") from exc
        log_audit(actor, "create", "professional_service", row.id, _audit_details(name=row.name))


def update_professional_service(service_id, category_id, name, description, icon, display_order, is_active) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ProfessionalService, service_id)
        if not row:
            raise ValueError("Service not found.")
        if not session.get(ServiceCategory, category_id):
            raise ValueError("Service category not found.")
        normalized_name = str(name).strip()[:255]
        if not normalized_name:
            raise ValueError("Service name is required.")
        duplicate = session.scalar(
            select(ProfessionalService.id).where(
                ProfessionalService.category_id == category_id,
                func.lower(ProfessionalService.name) == normalized_name.lower(),
                ProfessionalService.id != service_id,
            )
        )
        if duplicate:
            raise ValueError("That service already exists in this category.")
        row.category_id = category_id
        row.name = normalized_name
        row.description = str(description).strip()
        row.icon = str(icon).strip()[:100] or "fa-camera"
        row.display_order = max(0, int(display_order or 0))
        row.is_active = bool(is_active)
        session.commit()
        log_audit(actor, "update", "professional_service", service_id, _audit_details(name=row.name))


def delete_professional_service(service_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ProfessionalService, service_id)
        if row:
            name = row.name
            session.delete(row)
            session.commit()
            log_audit(actor, "delete", "professional_service", service_id, _audit_details(name=name))


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


def get_all_users() -> list[_Row]:
    with SessionLocal() as session:
        return _to_rows(session.scalars(select(User).order_by(User.created_at)).all())


def create_user(name: str, email: str, password: str) -> None:
    name = str(name).strip()[:255]
    email = str(email).strip().lower()[:255]
    if not name or "@" not in email:
        raise ValueError("A name and valid email address are required.")
    if len(password or "") < 10:
        raise ValueError("Password must be at least 10 characters.")
    actor = _actor_email()
    with SessionLocal() as session:
        if session.scalar(select(User.id).where(func.lower(User.email) == email)):
            raise ValueError("An administrator with that email already exists.")
        row = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin",
            is_active=True,
        )
        session.add(row)
        session.commit()
        log_audit(actor, "create", "user", row.id, _audit_details(email=email))


def update_user(user_id: int, name: str, email: str, is_active: bool, password: str = "") -> None:
    name = str(name).strip()[:255]
    email = str(email).strip().lower()[:255]
    if not name or "@" not in email:
        raise ValueError("A name and valid email address are required.")
    if password and len(password) < 10:
        raise ValueError("Password must be at least 10 characters.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(User, user_id)
        if not row:
            raise ValueError("Administrator not found.")
        duplicate = session.scalar(
            select(User.id).where(func.lower(User.email) == email, User.id != user_id)
        )
        if duplicate:
            raise ValueError("An administrator with that email already exists.")
        if not is_active:
            active_count = session.scalar(
                select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
            )
            if active_count <= 1:
                raise ValueError("The last active administrator cannot be disabled.")
        row.name = name
        row.email = email
        row.is_active = bool(is_active)
        if password:
            row.password_hash = generate_password_hash(password)
            row.auth_version += 1
        session.commit()
        log_audit(actor, "update", "user", user_id, _audit_details(email=email, active=is_active))


def record_user_login(user_id: int) -> None:
    with SessionLocal() as session:
        row = session.get(User, user_id)
        if row:
            row.last_login_at = datetime.utcnow()
            session.commit()


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
            select(Expense)
            .options(selectinload(Expense.asset))
            .where(Expense.is_deleted == False)  # noqa: E712
            .order_by(
                case((Expense.payment_status == "pending", 0), else_=1),
                Expense.due_date.asc().nullslast(),
                Expense.date.desc(),
            )
        ).all()
        return _to_rows(rows)


def add_expense(
    date, description, category, amount, asset_id=None, payment_status="paid",
    payee="", due_date=None, paid_date=None,
) -> None:
    amount = _validate_positive_amount(amount, "Expense amount")
    date = _validate_date(date, "Expense date")
    if not str(description).strip():
        raise ValueError("Description is required.")
    if not str(category).strip():
        raise ValueError("Category is required.")
    if payment_status not in {"pending", "paid", "cancelled"}:
        raise ValueError("Invalid payment status.")
    due_date = _validate_optional_date(due_date, "Due date")
    paid_date = _validate_optional_date(paid_date, "Paid date")
    if payment_status == "paid" and paid_date is None:
        paid_date = date
    actor = _actor_email()
    with SessionLocal() as session:
        if asset_id and not session.get(Asset, asset_id):
            raise ValueError("Selected asset does not exist.")
        row = Expense(
            date=date,
            description=description,
            category=category,
            amount=amount,
            asset_id=asset_id or None,
            payment_status=payment_status,
            payee=str(payee).strip()[:255],
            due_date=due_date,
            paid_date=paid_date,
        )
        session.add(row)
        session.commit()
        log_audit(actor, "create", "expense", row.id,
                  _audit_details(description=description, category=category, amount=amount))


def update_expense(
    expense_id: int, date, description, category, amount, asset_id=None,
    payment_status="paid", payee="", due_date=None, paid_date=None,
) -> None:
    amount = _validate_positive_amount(amount, "Expense amount")
    date = _validate_date(date, "Expense date")
    if payment_status not in {"pending", "paid", "cancelled"}:
        raise ValueError("Invalid payment status.")
    due_date = _validate_optional_date(due_date, "Due date")
    paid_date = _validate_optional_date(paid_date, "Paid date")
    if payment_status == "paid" and paid_date is None:
        paid_date = date
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(Expense, expense_id)
        if row and not row.is_deleted:
            if asset_id and not session.get(Asset, asset_id):
                raise ValueError("Selected asset does not exist.")
            row.date = date
            row.description = str(description).strip()
            row.category = str(category).strip()
            row.amount = amount
            row.asset_id = asset_id or None
            row.payment_status = payment_status
            row.payee = str(payee).strip()[:255]
            row.due_date = due_date
            row.paid_date = paid_date
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
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.is_deleted == False,  # noqa: E712
                Expense.payment_status == "paid",
            )
        )
        return float(total)


def get_outstanding_expenses_total() -> float:
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.is_deleted == False,  # noqa: E712
                Expense.payment_status == "pending",
            )
        )
        return float(total)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def get_all_customers() -> list[_Row]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(Customer)
            .where(Customer.is_deleted == False)  # noqa: E712
            .order_by(
                case((Customer.amount_paid < Customer.total_amount, 0), else_=1),
                (Customer.total_amount - Customer.amount_paid).desc(),
                Customer.created_at.desc(),
            )
        ).all()
        return _to_rows(rows)


def get_customer(customer_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.scalar(
            select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)  # noqa: E712
        )
        return _to_row(row)


def add_customer(name, service, amount_paid, total_amount, contact, location="") -> None:
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
                       total_amount=total_amount, contact=contact,
                       location=str(location).strip()[:500])
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


def update_customer(customer_id: int, name, service, amount_paid, total_amount, contact, location="") -> None:
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
            row.location = str(location).strip()[:500]
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
        rows = session.execute(
            select(
                Asset,
                func.coalesce(func.sum(Expense.amount), 0).label("expense_total"),
            )
            .outerjoin(
                Expense,
                (Expense.asset_id == Asset.id) & (Expense.is_deleted == False),  # noqa: E712
            )
            .group_by(Asset.id)
            .order_by(Asset.created_at.desc())
        ).all()
        result = []
        for asset, expense_total in rows:
            item = _to_row(asset)
            item["expense_total"] = float(expense_total)
            result.append(item)
        return result


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


def get_published_gallery_images(album=None, limit=None, search="") -> list[_Row]:
    with SessionLocal() as session:
        q = select(GalleryImage).where(
            GalleryImage.published == True,  # noqa: E712
            GalleryImage.is_deleted == False,  # noqa: E712
        )
        if album:
            q = q.where(GalleryImage.album == album)
        if search:
            pattern = f"%{str(search).strip()}%"
            q = q.where(
                or_(GalleryImage.caption.ilike(pattern), GalleryImage.album.ilike(pattern))
            )
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
    tiktok_url,
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
            row.tiktok_url = tiktok_url
            row.whatsapp_number = whatsapp_number
            row.updated_at = datetime.utcnow()
            row_id = row.id
        else:
            new_row = WebsiteSettings(
                site_name=site_name, hero_text=hero_text, hero_subtext=hero_subtext,
                about_text=about_text, contact_phone=contact_phone,
                contact_email=contact_email, address=address,
                facebook_url=facebook_url, instagram_url=instagram_url,
                youtube_url=youtube_url, tiktok_url=tiktok_url,
                whatsapp_number=whatsapp_number,
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
            .options(selectinload(Expense.asset))
            .where(Expense.is_deleted == False, Expense.date.between(start_date, end_date))  # noqa: E712
            .order_by(Expense.date.desc())
        ).all()
        return _to_rows(rows)


def get_financial_report(start_date, end_date, detail_limit: int = 500) -> _Row:
    """Return database-calculated totals and bounded report detail rows."""
    detail_limit = max(1, min(int(detail_limit), 1000))
    income_filter = (
        Income.is_deleted == False,  # noqa: E712
        Income.date.between(start_date, end_date),
    )
    expense_filter = (
        Expense.is_deleted == False,  # noqa: E712
        Expense.date.between(start_date, end_date),
    )

    with SessionLocal() as session:
        total_income, income_count = session.execute(
            select(func.coalesce(func.sum(Income.amount), 0), func.count(Income.id))
            .where(*income_filter)
        ).one()
        total_expenses, expense_count = session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))
            .where(*expense_filter)
        ).one()
        income_rows = session.scalars(
            select(Income)
            .where(*income_filter)
            .order_by(Income.date.desc(), Income.id.desc())
            .limit(detail_limit)
        ).all()
        expense_rows = session.scalars(
            select(Expense)
            .options(selectinload(Expense.asset))
            .where(*expense_filter)
            .order_by(Expense.date.desc(), Expense.id.desc())
            .limit(detail_limit)
        ).all()

        return _Row({
            "income_records": _to_rows(income_rows),
            "expense_records": _to_rows(expense_rows),
            "total_income": total_income,
            "total_expenses": total_expenses,
            "income_count": int(income_count),
            "expense_count": int(expense_count),
            "detail_limit": detail_limit,
        })


def get_recent_transactions(limit: int = 10) -> list[_Row]:
    """Return recent income + expense combined, sorted by date."""
    with SessionLocal() as session:
        income_rows = session.scalars(
            select(Income).where(Income.is_deleted == False).order_by(Income.date.desc()).limit(limit)  # noqa: E712
        ).all()
        expense_rows = session.scalars(
            select(Expense)
            .options(selectinload(Expense.asset))
            .where(Expense.is_deleted == False)  # noqa: E712
            .order_by(Expense.date.desc())
            .limit(limit)
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
# Private client collections
# ---------------------------------------------------------------------------
def generate_collection_code(title: str) -> str:
    base = "".join(ch for ch in str(title).upper() if ch.isalnum())[:12] or "GALLERY"
    return f"{base}-{secrets.token_hex(3).upper()}"


def get_all_client_collections(search: str = "", status: str = "all") -> list[_Row]:
    with SessionLocal() as session:
        image_count = (
            select(
                ClientCollectionImage.collection_id,
                func.count(ClientCollectionImage.id).label("image_count"),
            )
            .group_by(ClientCollectionImage.collection_id)
            .subquery()
        )
        download_count = (
            select(
                GalleryDownload.collection_id,
                func.count(GalleryDownload.id).label("download_count"),
            )
            .group_by(GalleryDownload.collection_id)
            .subquery()
        )
        unread_download_count = (
            select(
                GalleryDownload.collection_id,
                func.count(GalleryDownload.id).label("unread_download_count"),
            )
            .where(GalleryDownload.is_seen == False)  # noqa: E712
            .group_by(GalleryDownload.collection_id)
            .subquery()
        )
        fallback_cover_image_id = (
            select(ClientCollectionImage.id)
            .where(ClientCollectionImage.collection_id == ClientCollection.id)
            .order_by(ClientCollectionImage.display_order, ClientCollectionImage.id)
            .limit(1)
            .scalar_subquery()
        )
        query = (
            select(
                ClientCollection,
                func.coalesce(image_count.c.image_count, 0),
                func.coalesce(download_count.c.download_count, 0),
                func.coalesce(unread_download_count.c.unread_download_count, 0),
                func.coalesce(
                    ClientCollection.cover_image_id,
                    fallback_cover_image_id,
                ).label("resolved_cover_image_id"),
            )
            .outerjoin(image_count, image_count.c.collection_id == ClientCollection.id)
            .outerjoin(download_count, download_count.c.collection_id == ClientCollection.id)
            .outerjoin(
                unread_download_count,
                unread_download_count.c.collection_id == ClientCollection.id,
            )
            .order_by(ClientCollection.created_at.desc())
        )
        search = str(search).strip()
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    ClientCollection.title.ilike(pattern),
                    ClientCollection.client_name.ilike(pattern),
                    ClientCollection.collection_code.ilike(pattern),
                    ClientCollection.location.ilike(pattern),
                )
            )
        now = datetime.utcnow()
        if status == "active":
            query = query.where(
                ClientCollection.is_active == True,  # noqa: E712
                or_(ClientCollection.expires_at.is_(None), ClientCollection.expires_at >= now),
            )
        elif status == "locked":
            query = query.where(
                ClientCollection.is_active == False,  # noqa: E712
                or_(ClientCollection.expires_at.is_(None), ClientCollection.expires_at >= now),
            )
        elif status == "expired":
            query = query.where(ClientCollection.expires_at < now)
        rows = session.execute(query).all()
        result = []
        for collection, images, downloads, unread_downloads, cover_id in rows:
            item = _to_row(collection)
            item["image_count"] = int(images)
            item["download_count"] = int(downloads)
            item["unread_download_count"] = int(unread_downloads)
            item["cover_image_id"] = cover_id
            if collection.expires_at and collection.expires_at < now:
                item["access_status"] = "expired"
            elif collection.is_active:
                item["access_status"] = "active"
            else:
                item["access_status"] = "locked"
            result.append(item)
        return result


def get_public_client_collections(search: str = "") -> list[_Row]:
    return get_all_client_collections(search=search, status="active")


def get_client_collection(collection_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        row = session.scalar(
            select(ClientCollection)
            .options(selectinload(ClientCollection.images))
            .where(ClientCollection.id == collection_id)
        )
        if not row:
            return None
        result = _to_row(row)
        result["images"] = _to_rows(row.images)
        return result


def get_client_collection_by_code(code: str, active_only: bool = False) -> Optional[_Row]:
    with SessionLocal() as session:
        query = select(ClientCollection).where(
            func.upper(ClientCollection.collection_code) == str(code).strip().upper()
        )
        if active_only:
            query = query.where(ClientCollection.is_active == True)  # noqa: E712
        row = session.scalar(query)
        if not row:
            return None
        result = _to_row(row)
        result["pin_hash"] = row.pin_hash
        return result


def add_client_collection(
    title, client_name, client_email, description, location, event_date,
    expires_at, pin, collection_code=None, created_by_id=None,
) -> _Row:
    title = str(title).strip()[:255]
    client_name = str(client_name).strip()[:255]
    pin = str(pin).strip()
    if not title or not client_name:
        raise ValueError("Collection title and client name are required.")
    if len(pin) < 4:
        raise ValueError("Collection PIN must contain at least 4 characters.")
    if len(pin) > 64:
        raise ValueError("Collection PIN cannot exceed 64 characters.")
    code = str(collection_code or generate_collection_code(title)).strip().upper()[:80]
    actor = _actor_email()
    with SessionLocal() as session:
        row = ClientCollection(
            title=title,
            collection_code=code,
            client_name=client_name,
            client_email=str(client_email).strip().lower()[:255],
            description=str(description).strip(),
            location=str(location).strip()[:500],
            event_date=_validate_optional_date(event_date, "Event date"),
            expires_at=(
                datetime.strptime(str(expires_at), "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                if expires_at else None
            ),
            pin_hash=generate_password_hash(pin),
            created_by_id=created_by_id,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("That collection code is already in use.") from exc
        log_audit(actor, "create", "client_collection", row.id, _audit_details(code=code, title=title))
        return _to_row(row)


def update_client_collection(
    collection_id, title, client_name, client_email, description, location,
    event_date, expires_at, is_active,
) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ClientCollection, collection_id)
        if not row:
            raise ValueError("Client collection not found.")
        row.title = str(title).strip()[:255]
        row.client_name = str(client_name).strip()[:255]
        row.client_email = str(client_email).strip().lower()[:255]
        row.description = str(description).strip()
        row.location = str(location).strip()[:500]
        row.event_date = _validate_optional_date(event_date, "Event date")
        row.expires_at = (
            datetime.strptime(str(expires_at), "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            if expires_at else None
        )
        row.is_active = bool(is_active)
        row.updated_at = datetime.utcnow()
        session.commit()
        log_audit(actor, "update", "client_collection", collection_id, _audit_details(title=row.title))


def reset_client_collection_pin(collection_id: int, pin: str) -> None:
    pin = str(pin).strip()
    if len(pin) < 4:
        raise ValueError("Collection PIN must contain at least 4 characters.")
    if len(pin) > 64:
        raise ValueError("Collection PIN cannot exceed 64 characters.")
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ClientCollection, collection_id)
        if not row:
            raise ValueError("Client collection not found.")
        row.pin_hash = generate_password_hash(pin)
        row.updated_at = datetime.utcnow()
        session.commit()
        log_audit(actor, "reset_pin", "client_collection", collection_id, _audit_details())


def delete_client_collection(collection_id: int) -> Optional[_Row]:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.scalar(
            select(ClientCollection)
            .options(selectinload(ClientCollection.images))
            .where(ClientCollection.id == collection_id)
        )
        if not row:
            return None
        result = _to_row(row)
        result["filenames"] = [image.filename for image in row.images]
        session.delete(row)
        session.commit()
        log_audit(actor, "delete", "client_collection", collection_id, _audit_details(title=row.title))
        return result


def add_client_collection_image(collection_id, filename, original_name, caption="", display_order=0) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        collection = session.get(ClientCollection, collection_id)
        if not collection:
            raise ValueError("Client collection not found.")
        row = ClientCollectionImage(
            collection_id=collection_id,
            filename=filename,
            original_name=str(original_name).strip()[:255],
            caption=str(caption).strip()[:1000],
            display_order=max(0, int(display_order or 0)),
        )
        session.add(row)
        session.flush()
        if collection.cover_image_id is None:
            collection.cover_image_id = row.id
        collection.updated_at = datetime.utcnow()
        session.commit()
        log_audit(actor, "create", "client_collection_image", row.id, _audit_details(collection_id=collection_id))


def get_client_collection_image(image_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        return _to_row(session.get(ClientCollectionImage, image_id))


def get_collection_cover_image(collection_id: int) -> Optional[_Row]:
    with SessionLocal() as session:
        collection = session.get(ClientCollection, collection_id)
        if not collection:
            return None
        if collection.cover_image_id:
            selected = session.get(ClientCollectionImage, collection.cover_image_id)
            if selected and selected.collection_id == collection_id:
                return _to_row(selected)
        row = session.scalar(
            select(ClientCollectionImage)
            .where(ClientCollectionImage.collection_id == collection_id)
            .order_by(ClientCollectionImage.display_order, ClientCollectionImage.id)
            .limit(1)
        )
        return _to_row(row)


def set_client_collection_cover(collection_id: int, image_id: int) -> None:
    actor = _actor_email()
    with SessionLocal() as session:
        collection = session.get(ClientCollection, collection_id)
        image = session.get(ClientCollectionImage, image_id)
        if not collection or not image or image.collection_id != collection_id:
            raise ValueError("That photo does not belong to this collection.")
        collection.cover_image_id = image.id
        collection.updated_at = datetime.utcnow()
        session.commit()
        log_audit(
            actor,
            "set_cover",
            "client_collection",
            collection_id,
            _audit_details(image_id=image_id),
        )


def delete_client_collection_image(image_id: int) -> Optional[_Row]:
    actor = _actor_email()
    with SessionLocal() as session:
        row = session.get(ClientCollectionImage, image_id)
        if not row:
            return None
        result = _to_row(row)
        session.delete(row)
        session.commit()
        log_audit(actor, "delete", "client_collection_image", image_id, _audit_details(collection_id=result["collection_id"]))
        return result


def unlock_client_collection(code: str, email: str, name: str, pin: str) -> Optional[_Row]:
    email = str(email).strip().lower()[:255]
    pin = str(pin).strip()
    if "@" not in email:
        raise ValueError("A valid email address is required.")
    with SessionLocal() as session:
        collection = session.scalar(
            select(ClientCollection).where(
                func.upper(ClientCollection.collection_code) == str(code).strip().upper(),
                ClientCollection.is_active == True,  # noqa: E712
            )
        )
        if not collection or (collection.expires_at and collection.expires_at < datetime.utcnow()):
            return None
        if not check_password_hash(collection.pin_hash, pin):
            return None
        visitor = session.scalar(
            select(GalleryVisitor).where(
                GalleryVisitor.collection_id == collection.id,
                func.lower(GalleryVisitor.email) == email,
            )
        )
        if visitor:
            visitor.name = str(name).strip()[:255] or visitor.name
            visitor.last_accessed_at = datetime.utcnow()
        else:
            visitor = GalleryVisitor(
                collection_id=collection.id,
                email=email,
                name=str(name).strip()[:255],
            )
            session.add(visitor)
        session.commit()
        result = _to_row(collection)
        result["visitor_id"] = visitor.id
        return result


def get_collection_images_for_visitor(collection_id: int, search: str = "") -> list[_Row]:
    with SessionLocal() as session:
        query = select(ClientCollectionImage).where(ClientCollectionImage.collection_id == collection_id)
        search = str(search).strip()
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    ClientCollectionImage.caption.ilike(pattern),
                    ClientCollectionImage.original_name.ilike(pattern),
                )
            )
        rows = session.scalars(
            query.order_by(ClientCollectionImage.display_order, ClientCollectionImage.id)
        ).all()
        return _to_rows(rows)


def add_gallery_download(collection_id, visitor_id, image_id=None, download_type="image") -> None:
    with SessionLocal() as session:
        session.add(GalleryDownload(
            collection_id=collection_id,
            image_id=image_id,
            visitor_id=visitor_id,
            download_type=download_type,
            ip_address=_client_ip()[:64],
        ))
        session.commit()


def get_unread_gallery_download_count(collection_id: int = None) -> int:
    with SessionLocal() as session:
        query = select(func.count(GalleryDownload.id)).where(
            GalleryDownload.is_seen == False  # noqa: E712
        )
        if collection_id is not None:
            query = query.where(GalleryDownload.collection_id == int(collection_id))
        return int(session.scalar(query) or 0)


def get_gallery_download_notifications(unread_only: bool = False, limit: int = 200) -> list[_Row]:
    limit = max(1, min(int(limit), 500))
    with SessionLocal() as session:
        query = (
            select(
                GalleryDownload,
                ClientCollection.title,
                ClientCollection.client_name,
                GalleryVisitor.email,
                GalleryVisitor.name,
                ClientCollectionImage.original_name,
            )
            .join(ClientCollection, ClientCollection.id == GalleryDownload.collection_id)
            .outerjoin(GalleryVisitor, GalleryVisitor.id == GalleryDownload.visitor_id)
            .outerjoin(ClientCollectionImage, ClientCollectionImage.id == GalleryDownload.image_id)
            .order_by(GalleryDownload.downloaded_at.desc(), GalleryDownload.id.desc())
            .limit(limit)
        )
        if unread_only:
            query = query.where(GalleryDownload.is_seen == False)  # noqa: E712
        rows = session.execute(query).all()
        result = []
        for download, title, client_name, email, visitor_name, image_name in rows:
            item = _to_row(download)
            item["collection_title"] = title
            item["client_name"] = client_name
            item["visitor_email"] = email
            item["visitor_name"] = visitor_name or "Client"
            item["image_name"] = image_name
            result.append(item)
        return result


def mark_gallery_downloads_seen(download_id: int = None) -> int:
    with SessionLocal() as session:
        statement = update(GalleryDownload).where(GalleryDownload.is_seen == False)  # noqa: E712
        if download_id is not None:
            statement = statement.where(GalleryDownload.id == int(download_id))
        result = session.execute(statement.values(is_seen=True))
        session.commit()
        return int(result.rowcount or 0)


def add_gallery_comment(image_id: int, visitor_id: int, comment: str) -> None:
    comment = str(comment).strip()[:2000]
    if not comment:
        raise ValueError("Comment cannot be empty.")
    with SessionLocal() as session:
        image = session.get(ClientCollectionImage, image_id)
        visitor = session.get(GalleryVisitor, visitor_id)
        if not image or not visitor or visitor.collection_id != image.collection_id:
            raise ValueError("The photo is not available in this collection.")
        session.add(GalleryComment(image_id=image_id, visitor_id=visitor_id, comment=comment))
        session.commit()


def get_gallery_comments(collection_id: int) -> list[_Row]:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                GalleryComment,
                GalleryVisitor.email,
                GalleryVisitor.name,
                ClientCollectionImage.original_name,
            )
            .join(GalleryVisitor, GalleryVisitor.id == GalleryComment.visitor_id)
            .join(ClientCollectionImage, ClientCollectionImage.id == GalleryComment.image_id)
            .where(ClientCollectionImage.collection_id == collection_id)
            .order_by(GalleryComment.created_at.desc())
        ).all()
        result = []
        for comment, email, visitor_name, filename in rows:
            item = _to_row(comment)
            item["visitor_email"] = email
            item["visitor_name"] = visitor_name or "Guest"
            item["image_name"] = filename
            result.append(item)
        return result


def toggle_gallery_like(image_id: int, visitor_id: int) -> bool:
    """Toggle a visitor's like and return True when the photo is now liked."""
    with SessionLocal() as session:
        image = session.get(ClientCollectionImage, image_id)
        visitor = session.get(GalleryVisitor, visitor_id)
        if not image or not visitor or visitor.collection_id != image.collection_id:
            raise ValueError("The photo is not available in this collection.")
        existing = session.scalar(
            select(GalleryLike).where(
                GalleryLike.image_id == image_id,
                GalleryLike.visitor_id == visitor_id,
            )
        )
        if existing:
            session.delete(existing)
            liked = False
        else:
            session.add(GalleryLike(image_id=image_id, visitor_id=visitor_id))
            liked = True
        session.commit()
        return liked


def get_gallery_like_summary(collection_id: int, visitor_id: int = None) -> dict:
    with SessionLocal() as session:
        count_rows = session.execute(
            select(GalleryLike.image_id, func.count(GalleryLike.id))
            .join(ClientCollectionImage, ClientCollectionImage.id == GalleryLike.image_id)
            .where(ClientCollectionImage.collection_id == collection_id)
            .group_by(GalleryLike.image_id)
        ).all()
        liked_image_ids = set()
        if visitor_id:
            liked_image_ids = set(session.scalars(
                select(GalleryLike.image_id)
                .join(ClientCollectionImage, ClientCollectionImage.id == GalleryLike.image_id)
                .where(
                    ClientCollectionImage.collection_id == collection_id,
                    GalleryLike.visitor_id == visitor_id,
                )
            ).all())
        return {
            "counts": {image_id: int(count) for image_id, count in count_rows},
            "liked_image_ids": liked_image_ids,
        }


def get_gallery_likes(collection_id: int) -> list[_Row]:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                GalleryLike,
                GalleryVisitor.email,
                GalleryVisitor.name,
                ClientCollectionImage.original_name,
            )
            .join(GalleryVisitor, GalleryVisitor.id == GalleryLike.visitor_id)
            .join(ClientCollectionImage, ClientCollectionImage.id == GalleryLike.image_id)
            .where(ClientCollectionImage.collection_id == collection_id)
            .order_by(GalleryLike.created_at.desc())
            .limit(500)
        ).all()
        result = []
        for like, email, visitor_name, filename in rows:
            item = _to_row(like)
            item["visitor_email"] = email
            item["visitor_name"] = visitor_name or "Guest"
            item["image_name"] = filename
            result.append(item)
        return result


def get_collection_activity(collection_id: int) -> dict:
    with SessionLocal() as session:
        visitors = session.scalars(
            select(GalleryVisitor)
            .where(GalleryVisitor.collection_id == collection_id)
            .order_by(GalleryVisitor.last_accessed_at.desc())
        ).all()
        downloads = session.execute(
            select(GalleryDownload, GalleryVisitor.email, ClientCollectionImage.original_name)
            .outerjoin(GalleryVisitor, GalleryVisitor.id == GalleryDownload.visitor_id)
            .outerjoin(ClientCollectionImage, ClientCollectionImage.id == GalleryDownload.image_id)
            .where(GalleryDownload.collection_id == collection_id)
            .order_by(GalleryDownload.downloaded_at.desc())
            .limit(200)
        ).all()
        download_rows = []
        for download, email, image_name in downloads:
            item = _to_row(download)
            item["visitor_email"] = email
            item["image_name"] = image_name
            download_rows.append(item)
        return {
            "visitors": _to_rows(visitors),
            "downloads": download_rows,
            "comments": get_gallery_comments(collection_id),
            "likes": get_gallery_likes(collection_id),
        }


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
