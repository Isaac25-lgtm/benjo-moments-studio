"""PostgreSQL integrity, invoice settlement, and social settings

Revision ID: 8b31a71f42d9
Revises: c5ed6f7e7dc4
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8b31a71f42d9"
down_revision: Union[str, None] = "c5ed6f7e7dc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE invoices
        SET status = CASE
            WHEN lower(status) IN ('pending', 'paid', 'cancelled') THEN lower(status)
            ELSE 'pending'
        END
        """
    )
    op.alter_column("invoices", "status", server_default="pending")

    op.add_column("income", sa.Column("source_invoice_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_income_source_invoice",
        "income",
        "invoices",
        ["source_invoice_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_income_source_invoice_id",
        "income",
        ["source_invoice_id"],
    )

    op.add_column("website_settings", sa.Column("facebook_url", sa.String(500), nullable=True))
    op.add_column("website_settings", sa.Column("instagram_url", sa.String(500), nullable=True))
    op.add_column("website_settings", sa.Column("youtube_url", sa.String(500), nullable=True))
    op.add_column("website_settings", sa.Column("whatsapp_number", sa.String(30), nullable=True))
    op.execute(
        "UPDATE website_settings SET whatsapp_number = '256759989861' "
        "WHERE whatsapp_number IS NULL"
    )

    op.create_check_constraint("ck_income_amount_positive", "income", "amount > 0")
    op.create_check_constraint("ck_expenses_amount_positive", "expenses", "amount > 0")
    op.create_check_constraint("ck_customers_total_positive", "customers", "total_amount > 0")
    op.create_check_constraint("ck_customers_paid_nonnegative", "customers", "amount_paid >= 0")
    op.create_check_constraint(
        "ck_customers_paid_within_total",
        "customers",
        "amount_paid <= total_amount",
    )
    op.create_check_constraint("ck_invoices_amount_positive", "invoices", "amount > 0")
    op.create_check_constraint(
        "ck_invoices_status",
        "invoices",
        "status IN ('pending', 'paid', 'cancelled')",
    )
    op.create_check_constraint("ck_assets_value_positive", "assets", "value > 0")
    op.create_check_constraint("ck_pricing_price_positive", "pricing_packages", "price > 0")
    op.create_check_constraint(
        "ck_pricing_order_nonnegative",
        "pricing_packages",
        "display_order >= 0",
    )

    op.create_index("ix_invoices_customer_active", "invoices", ["customer_id", "is_deleted"])
    op.create_index("ix_contact_messages_unread", "contact_messages", ["is_read", "created_at"])
    op.create_index("ix_gallery_active", "gallery", ["is_deleted", "published", "album"])


def downgrade() -> None:
    op.drop_index("ix_gallery_active", table_name="gallery")
    op.drop_index("ix_contact_messages_unread", table_name="contact_messages")
    op.drop_index("ix_invoices_customer_active", table_name="invoices")

    op.drop_constraint("ck_pricing_order_nonnegative", "pricing_packages", type_="check")
    op.drop_constraint("ck_pricing_price_positive", "pricing_packages", type_="check")
    op.drop_constraint("ck_assets_value_positive", "assets", type_="check")
    op.drop_constraint("ck_invoices_status", "invoices", type_="check")
    op.drop_constraint("ck_invoices_amount_positive", "invoices", type_="check")
    op.drop_constraint("ck_customers_paid_within_total", "customers", type_="check")
    op.drop_constraint("ck_customers_paid_nonnegative", "customers", type_="check")
    op.drop_constraint("ck_customers_total_positive", "customers", type_="check")
    op.drop_constraint("ck_expenses_amount_positive", "expenses", type_="check")
    op.drop_constraint("ck_income_amount_positive", "income", type_="check")

    op.drop_column("website_settings", "whatsapp_number")
    op.drop_column("website_settings", "youtube_url")
    op.drop_column("website_settings", "instagram_url")
    op.drop_column("website_settings", "facebook_url")

    op.drop_constraint("uq_income_source_invoice_id", "income", type_="unique")
    op.drop_constraint("fk_income_source_invoice", "income", type_="foreignkey")
    op.drop_column("income", "source_invoice_id")
    op.alter_column("invoices", "status", server_default="Pending")
