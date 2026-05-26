"""questionnaire rule fields

Revision ID: 202605260003_questionnaire_rule_fields
Revises: 202605260004
Create Date: 2026-05-26 16:20:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260003_questionnaire_rule_fields"
down_revision: Union[str, None] = "202605260004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


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
    _add_column_if_missing("questionnaires", sa.Column("builtin_content_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing("questions", sa.Column("code", sa.String(length=100), nullable=True))
    _add_column_if_missing("answer_records", sa.Column("selected_display_index", sa.Integer(), nullable=True))

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE questionnaires SET source_type = 'school_custom' WHERE source_type IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET disclaimer = '' WHERE disclaimer IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET dimensions = '[]' WHERE dimensions IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET scoring_rule = '{}' WHERE scoring_rule IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET risk_rules = '{}' WHERE risk_rules IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET quality_rules = '{}' WHERE quality_rules IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET builtin_content_hash = '' WHERE builtin_content_hash IS NULL"))
    bind.execute(sa.text("UPDATE answer_records SET selected_display_index = 0 WHERE selected_display_index IS NULL"))

    index_name = "uq_questionnaires_code_not_null"
    if index_name not in _indexes("questionnaires"):
        dialect = bind.dialect.name
        if dialect == "sqlite":
            op.execute(sa.text(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON questionnaires(code) WHERE code IS NOT NULL"))
        else:
            with op.batch_alter_table("questionnaires") as batch:
                batch.create_index(index_name, ["code"], unique=True)


def downgrade() -> None:
    pass
