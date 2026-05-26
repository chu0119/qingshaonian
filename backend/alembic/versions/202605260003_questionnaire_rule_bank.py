"""questionnaire rule bank fields

Revision ID: 202605260003
Revises: 202605260002
Create Date: 2026-05-26 00:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260003"
down_revision: Union[str, None] = "202605260002"
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
    _add_column_if_missing("questionnaires", sa.Column("code", sa.String(length=100), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("source_type", sa.String(length=50), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("disclaimer", sa.Text(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("dimensions", sa.JSON(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("scoring_rule", sa.JSON(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("risk_rules", sa.JSON(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("quality_rules", sa.JSON(), nullable=True))
    _add_column_if_missing("questions", sa.Column("code", sa.String(length=100), nullable=True))

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE questionnaires SET source_type = 'school_custom' WHERE source_type IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET disclaimer = '' WHERE disclaimer IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET dimensions = '[]' WHERE dimensions IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET scoring_rule = '{}' WHERE scoring_rule IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET risk_rules = '{}' WHERE risk_rules IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET quality_rules = '{}' WHERE quality_rules IS NULL"))


def downgrade() -> None:
    pass
