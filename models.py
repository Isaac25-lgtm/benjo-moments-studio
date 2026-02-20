"""
SQLAlchemy ORM models for Benjo Moments Photography System.

These models mirror the existing SQLite schema exactly so that Alembic can
generate a clean initial migration. Field types are chosen to work correctly
on both SQLite (fallback) and PostgreSQL (production).

DO NOT import this module before db.py — it depends on Base from here.
"""
import secrets
from datetime import datetime, date as date_type

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
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
# Expenses
# ---------------------------------------------------------------------------
class Expense(Base):
    __tablename__ = "expenses"

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    status = Column(String(50), nullable=False, default="Pending")
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

