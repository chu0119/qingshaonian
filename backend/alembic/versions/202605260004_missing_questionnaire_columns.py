"""add missing columns for questionnaire model fields

Revision ID: 202605260004
Revises: 202605260003
Create Date: 2026-05-26 00:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260004"
down_revision: Union[str, None] = "202605260003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(column)


def upgrade() -> None:
    # Question fields that may not have been covered by earlier migrations
    _add_column_if_missing("questions", sa.Column("risk_threshold", sa.Integer(), nullable=True))

    # Option fields
    _add_column_if_missing("options", sa.Column("is_risk_option", sa.Boolean(), nullable=True))

    # Answer sheet fields
    _add_column_if_missing("answer_sheets", sa.Column("ip_address", sa.String(length=50), nullable=True))
    _add_column_if_missing("answer_sheets", sa.Column("user_agent", sa.String(length=500), nullable=True))

    # Set defaults for existing rows
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE options SET is_risk_option = 0 WHERE is_risk_option IS NULL"))
    bind.execute(sa.text("UPDATE answer_sheets SET ip_address = '' WHERE ip_address IS NULL"))
    bind.execute(sa.text("UPDATE answer_sheets SET user_agent = '' WHERE user_agent IS NULL"))


def downgrade() -> None:
    pass
