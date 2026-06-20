"""Add client photo likes

Revision ID: f3a8c6d9e2b1
Revises: d2f9a1c4e7b6
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f3a8c6d9e2b1"
down_revision: Union[str, None] = "d2f9a1c4e7b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gallery_likes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("visitor_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["image_id"], ["client_collection_images.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["visitor_id"], ["gallery_visitors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("image_id", "visitor_id", name="uq_gallery_like_image_visitor"),
    )
    op.create_index("ix_gallery_likes_image", "gallery_likes", ["image_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_gallery_likes_image", table_name="gallery_likes")
    op.drop_table("gallery_likes")
