"""Add missing indexes

Revision ID: 21bb5163e7ec
Revises: 718b23262d05
Create Date: 2026-06-27 15:35:14.873770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21bb5163e7ec'
down_revision: Union[str, None] = '718b23262d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index on status for filtered listings
    op.create_index("ix_assets_status", "assets", ["status"])

    # Composite index for the (type, value) lookup used in bulk import
    op.create_index("ix_assets_type_value", "assets", ["type", "value"])

    # GIN index for array-contains queries on tags
    op.execute("CREATE INDEX ix_assets_tags ON assets USING GIN (tags)")

    # Indexes on relationship FKs for neighbor traversal queries
    op.create_index("ix_relationships_source", "asset_relationships", ["source_asset_id"])
    op.create_index("ix_relationships_target", "asset_relationships", ["target_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_relationships_target", table_name="asset_relationships")
    op.drop_index("ix_relationships_source", table_name="asset_relationships")
    op.execute("DROP INDEX ix_assets_tags")
    op.drop_index("ix_assets_type_value", table_name="assets")
    op.drop_index("ix_assets_status", table_name="assets")
