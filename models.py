"""
SQLAlchemy ORM models for Benjo Moments Photography System.

These models define the PostgreSQL schema used locally and in production.

DO NOT import this module before db.py — it depends on Base from here.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------
class Income(Base):
    __tablename__ = "income"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_income_amount_positive"),
        Index("ix_income_date", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    source_invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        unique=True,
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "source_invoice_id": self.source_invoice_id,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------
class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        Index("ix_expenses_date", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("total_amount > 0", name="ck_customers_total_positive"),
        CheckConstraint("amount_paid >= 0", name="ck_customers_paid_nonnegative"),
        CheckConstraint("amount_paid <= total_amount", name="ck_customers_paid_within_total"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    service = Column(String(255), nullable=False)
    amount_paid = Column(Numeric(14, 2), nullable=False, default=0)
    total_amount = Column(Numeric(14, 2), nullable=False)
    contact = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    invoices = relationship(
        "Invoice", back_populates="customer", cascade="all, delete-orphan"
    )

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "service": self.service,
            "amount_paid": float(self.amount_paid),
            "total_amount": float(self.total_amount),
            "contact": self.contact,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------
class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')",
            name="ck_invoices_status",
        ),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_customer_active", "customer_id", "is_deleted"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="invoices")

    def as_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "date": self.date,
            "amount": float(self.amount),
            "status": self.status,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("value > 0", name="ck_assets_value_positive"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    value = Column(Numeric(14, 2), nullable=False)
    supplier = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "value": float(self.value),
            "supplier": self.supplier,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------
class GalleryImage(Base):
    __tablename__ = "gallery"
    __table_args__ = (
        Index("ix_gallery_album_published", "album", "published"),
        Index("ix_gallery_active", "is_deleted", "published", "album"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    album = Column(String(100), nullable=False)
    caption = Column(Text, nullable=True)
    published = Column(Boolean, nullable=False, default=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    def as_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "album": self.album,
            "caption": self.caption,
            "published": self.published,
            "uploaded_at": self.uploaded_at,
        }


# ---------------------------------------------------------------------------
# Website Settings (singleton row)
# ---------------------------------------------------------------------------
class WebsiteSettings(Base):
    __tablename__ = "website_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(255), nullable=False, default="Benjo Moments")
    hero_text = Column(Text, nullable=True, default="Capturing Your Precious Moments")
    hero_subtext = Column(Text, nullable=True, default="Professional Photography Services")
    about_text = Column(Text, nullable=True)
    contact_phone = Column(String(100), nullable=True, default="0759989861 / 0778728089")
    contact_email = Column(String(255), nullable=True, default="info@benjomoments.com")
    address = Column(Text, nullable=True)
    facebook_url = Column(String(500), nullable=True)
    instagram_url = Column(String(500), nullable=True)
    youtube_url = Column(String(500), nullable=True)
    whatsapp_number = Column(String(30), nullable=True, default="256759989861")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "site_name": self.site_name,
            "hero_text": self.hero_text,
            "hero_subtext": self.hero_subtext,
            "about_text": self.about_text,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "address": self.address,
            "facebook_url": self.facebook_url,
            "instagram_url": self.instagram_url,
            "youtube_url": self.youtube_url,
            "whatsapp_number": self.whatsapp_number,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Hero Images
# ---------------------------------------------------------------------------
class HeroImage(Base):
    __tablename__ = "hero_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "display_order": self.display_order,
            "uploaded_at": self.uploaded_at,
        }


# ---------------------------------------------------------------------------
# Contact Messages
# ---------------------------------------------------------------------------
class ContactMessage(Base):
    __tablename__ = "contact_messages"
    __table_args__ = (
        Index("ix_contact_messages_unread", "is_read", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(100), nullable=True)
    service = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "service": self.service,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Pricing Packages
# ---------------------------------------------------------------------------
class PricingPackage(Base):
    __tablename__ = "pricing_packages"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_pricing_price_positive"),
        CheckConstraint("display_order >= 0", name="ck_pricing_order_nonnegative"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)            # stored as integer (UGX)
    price_label = Column(String(50), nullable=False, default="/session")
    icon = Column(String(100), nullable=False, default="fa-camera")
    features = Column(Text, nullable=True)             # pipe-separated list
    is_featured = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "price_label": self.price_label,
            "icon": self.icon,
            "features": self.features,
            "is_featured": self.is_featured,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Audit Logs (Phase 10)
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)       # e.g. "create", "update", "delete"
    entity_type = Column(String(100), nullable=True)   # e.g. "income", "invoice"
    entity_id = Column(Integer, nullable=True)
    details_json = Column(Text, nullable=True)         # JSON string with extra context
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details_json": self.details_json,
            "created_at": self.created_at,
        }

