"""Client delivery, multi-admin, services, and operations

Revision ID: a74d3e91c2f0
Revises: 8b31a71f42d9
Create Date: 2026-06-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a74d3e91c2f0"
down_revision: Union[str, None] = "8b31a71f42d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("location", sa.String(500), nullable=True))

    op.add_column("expenses", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.add_column("expenses", sa.Column("payment_status", sa.String(20), server_default="paid", nullable=False))
    op.add_column("expenses", sa.Column("payee", sa.String(255), nullable=True))
    op.add_column("expenses", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("expenses", sa.Column("paid_date", sa.Date(), nullable=True))
    op.create_foreign_key(
        "fk_expenses_asset_id", "expenses", "assets", ["asset_id"], ["id"], ondelete="SET NULL"
    )
    op.create_check_constraint(
        "ck_expenses_payment_status",
        "expenses",
        "payment_status IN ('pending', 'paid', 'cancelled')",
    )
    op.create_index("ix_expenses_asset_active", "expenses", ["asset_id", "is_deleted"])
    op.create_index("ix_expenses_payment_status", "expenses", ["payment_status", "due_date"])

    op.add_column("website_settings", sa.Column("tiktok_url", sa.String(500), nullable=True))
    op.execute("UPDATE website_settings SET whatsapp_number = '256759189861'")

    op.create_table(
        "service_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=False, server_default="fa-camera"),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("display_order >= 0", name="ck_service_category_order_nonnegative"),
    )
    op.create_table(
        "professional_services",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=False, server_default="fa-camera"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("category_id", "name", name="uq_service_category_name"),
        sa.CheckConstraint("display_order >= 0", name="ck_professional_service_order_nonnegative"),
    )

    op.create_table(
        "client_collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("collection_code", sa.String(80), nullable=False, unique=True),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("pin_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_client_collections_active", "client_collections", ["is_active", "event_date"])
    op.create_table(
        "client_collection_images",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["client_collections.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_client_collection_images_collection",
        "client_collection_images",
        ["collection_id", "display_order"],
    )
    op.create_table(
        "gallery_visitors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("first_accessed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["client_collections.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("collection_id", "email", name="uq_gallery_visitor_collection_email"),
    )
    op.create_index("ix_gallery_visitors_collection", "gallery_visitors", ["collection_id", "last_accessed_at"])
    op.create_table(
        "gallery_downloads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("visitor_id", sa.Integer(), nullable=True),
        sa.Column("download_type", sa.String(20), nullable=False, server_default="image"),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["client_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["client_collection_images.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visitor_id"], ["gallery_visitors.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_gallery_downloads_collection", "gallery_downloads", ["collection_id", "downloaded_at"])
    op.create_table(
        "gallery_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("visitor_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["image_id"], ["client_collection_images.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["visitor_id"], ["gallery_visitors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_gallery_comments_image", "gallery_comments", ["image_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_gallery_comments_image", table_name="gallery_comments")
    op.drop_table("gallery_comments")
    op.drop_index("ix_gallery_downloads_collection", table_name="gallery_downloads")
    op.drop_table("gallery_downloads")
    op.drop_index("ix_gallery_visitors_collection", table_name="gallery_visitors")
    op.drop_table("gallery_visitors")
    op.drop_index("ix_client_collection_images_collection", table_name="client_collection_images")
    op.drop_table("client_collection_images")
    op.drop_index("ix_client_collections_active", table_name="client_collections")
    op.drop_table("client_collections")
    op.drop_table("professional_services")
    op.drop_table("service_categories")
    op.drop_column("website_settings", "tiktok_url")
    op.drop_index("ix_expenses_payment_status", table_name="expenses")
    op.drop_index("ix_expenses_asset_active", table_name="expenses")
    op.drop_constraint("ck_expenses_payment_status", "expenses", type_="check")
    op.drop_constraint("fk_expenses_asset_id", "expenses", type_="foreignkey")
    op.drop_column("expenses", "paid_date")
    op.drop_column("expenses", "due_date")
    op.drop_column("expenses", "payee")
    op.drop_column("expenses", "payment_status")
    op.drop_column("expenses", "asset_id")
    op.drop_column("customers", "location")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "is_active")
