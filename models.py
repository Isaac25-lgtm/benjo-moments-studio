"""
SQLAlchemy ORM models for Benjo Moments Photography System.

These models define the PostgreSQL schema used locally and in production.

DO NOT import this module before db.py — it depends on Base from here.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint, func,
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
    is_active = Column(Boolean, nullable=False, default=True)
    auth_version = Column(Integer, nullable=False, default=1)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "auth_version": self.auth_version,
            "last_login_at": self.last_login_at,
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
        CheckConstraint(
            "payment_status IN ('pending', 'paid', 'cancelled')",
            name="ck_expenses_payment_status",
        ),
        Index("ix_expenses_date", "date"),
        Index("ix_expenses_asset_active", "asset_id", "is_deleted"),
        Index("ix_expenses_payment_status", "payment_status", "due_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    payment_status = Column(String(20), nullable=False, default="paid")
    payee = Column(String(255), nullable=True)
    due_date = Column(Date, nullable=True)
    paid_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    asset = relationship("Asset", back_populates="expenses")

    def as_dict(self):
        loaded_asset = self.__dict__.get("asset")
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "asset_id": self.asset_id,
            "asset_name": loaded_asset.name if loaded_asset else None,
            "payment_status": self.payment_status,
            "payee": self.payee,
            "due_date": self.due_date,
            "paid_date": self.paid_date,
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
    location = Column(String(500), nullable=True)
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
            "location": self.location,
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

    expenses = relationship("Expense", back_populates="asset", passive_deletes=True)

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
# Private client delivery galleries
# ---------------------------------------------------------------------------
class ClientCollection(Base):
    __tablename__ = "client_collections"
    __table_args__ = (
        Index("ix_client_collections_active", "is_active", "event_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    collection_code = Column(String(80), unique=True, nullable=False)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    event_date = Column(Date, nullable=True)
    pin_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime, nullable=True)
    cover_image_id = Column(
        Integer,
        ForeignKey("client_collection_images.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        index=True,
    )
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship(
        "ClientCollectionImage",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="ClientCollectionImage.display_order, ClientCollectionImage.id",
        foreign_keys="ClientCollectionImage.collection_id",
    )

    def as_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "collection_code": self.collection_code,
            "client_name": self.client_name,
            "client_email": self.client_email,
            "description": self.description,
            "location": self.location,
            "event_date": self.event_date,
            "is_active": self.is_active,
            "expires_at": self.expires_at,
            "cover_image_id": self.cover_image_id,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ClientCollectionImage(Base):
    __tablename__ = "client_collection_images"
    __table_args__ = (
        Index("ix_client_collection_images_collection", "collection_id", "display_order"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("client_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    caption = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    collection = relationship(
        "ClientCollection",
        back_populates="images",
        foreign_keys=[collection_id],
    )

    def as_dict(self):
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "filename": self.filename,
            "original_name": self.original_name,
            "caption": self.caption,
            "display_order": self.display_order,
            "uploaded_at": self.uploaded_at,
        }


class GalleryVisitor(Base):
    __tablename__ = "gallery_visitors"
    __table_args__ = (
        UniqueConstraint("collection_id", "email", name="uq_gallery_visitor_collection_email"),
        Index("ix_gallery_visitors_collection", "collection_id", "last_accessed_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("client_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    first_accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "email": self.email,
            "name": self.name,
            "first_accessed_at": self.first_accessed_at,
            "last_accessed_at": self.last_accessed_at,
        }


class GalleryDownload(Base):
    __tablename__ = "gallery_downloads"
    __table_args__ = (
        Index("ix_gallery_downloads_collection", "collection_id", "downloaded_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("client_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_id = Column(
        Integer,
        ForeignKey("client_collection_images.id", ondelete="SET NULL"),
        nullable=True,
    )
    visitor_id = Column(
        Integer,
        ForeignKey("gallery_visitors.id", ondelete="SET NULL"),
        nullable=True,
    )
    download_type = Column(String(20), nullable=False, default="image")
    ip_address = Column(String(64), nullable=True)
    downloaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "image_id": self.image_id,
            "visitor_id": self.visitor_id,
            "download_type": self.download_type,
            "ip_address": self.ip_address,
            "downloaded_at": self.downloaded_at,
        }


class GalleryComment(Base):
    __tablename__ = "gallery_comments"
    __table_args__ = (
        Index("ix_gallery_comments_image", "image_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(
        Integer,
        ForeignKey("client_collection_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    visitor_id = Column(
        Integer,
        ForeignKey("gallery_visitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "image_id": self.image_id,
            "visitor_id": self.visitor_id,
            "comment": self.comment,
            "created_at": self.created_at,
        }


class GalleryLike(Base):
    __tablename__ = "gallery_likes"
    __table_args__ = (
        UniqueConstraint("image_id", "visitor_id", name="uq_gallery_like_image_visitor"),
        Index("ix_gallery_likes_image", "image_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(
        Integer,
        ForeignKey("client_collection_images.id", ondelete="CASCADE"),
        nullable=False,
    )
    visitor_id = Column(
        Integer,
        ForeignKey("gallery_visitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "image_id": self.image_id,
            "visitor_id": self.visitor_id,
            "created_at": self.created_at,
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
    tiktok_url = Column(String(500), nullable=True)
    whatsapp_number = Column(String(30), nullable=True, default="256759189861")
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
            "tiktok_url": self.tiktok_url,
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
# Editable public service catalogue
# ---------------------------------------------------------------------------
class ServiceCategory(Base):
    __tablename__ = "service_categories"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="ck_service_category_order_nonnegative"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=False, default="fa-camera")
    image_url = Column(String(1000), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    services = relationship(
        "ProfessionalService",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="ProfessionalService.display_order, ProfessionalService.id",
    )

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "image_url": self.image_url,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class ProfessionalService(Base):
    __tablename__ = "professional_services"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_service_category_name"),
        CheckConstraint("display_order >= 0", name="ck_professional_service_order_nonnegative"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(
        Integer,
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=False, default="fa-camera")
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("ServiceCategory", back_populates="services")

    def as_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
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

