"""Add unread state for client gallery downloads.

Revision ID: b7c2d4e9f1a3
Revises: f3a8c6d9e2b1
Create Date: 2026-06-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b7c2d4e9f1a3"
down_revision: Union[str, None] = "f3a8c6d9e2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gallery_downloads",
        sa.Column("is_seen", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE gallery_downloads SET is_seen = TRUE")
    op.alter_column(
        "gallery_downloads",
        "is_seen",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    op.create_index(
        "ix_gallery_downloads_unseen",
        "gallery_downloads",
        ["is_seen", "downloaded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_gallery_downloads_unseen", table_name="gallery_downloads")
    op.drop_column("gallery_downloads", "is_seen")
