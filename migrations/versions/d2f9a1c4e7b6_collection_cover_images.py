"""Add selectable cover images to client collections

Revision ID: d2f9a1c4e7b6
Revises: a74d3e91c2f0
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d2f9a1c4e7b6"
down_revision: Union[str, None] = "a74d3e91c2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("client_collections", sa.Column("cover_image_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_client_collections_cover_image_id",
        "client_collections",
        "client_collection_images",
        ["cover_image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_client_collections_cover_image_id",
        "client_collections",
        ["cover_image_id"],
    )
    op.execute(
        """
        UPDATE client_collections AS collection
        SET cover_image_id = first_image.id
        FROM (
            SELECT DISTINCT ON (collection_id) id, collection_id
            FROM client_collection_images
            ORDER BY collection_id, display_order, id
        ) AS first_image
        WHERE collection.id = first_image.collection_id
          AND collection.cover_image_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_client_collections_cover_image_id", table_name="client_collections")
    op.drop_constraint(
        "fk_client_collections_cover_image_id",
        "client_collections",
        type_="foreignkey",
    )
    op.drop_column("client_collections", "cover_image_id")
