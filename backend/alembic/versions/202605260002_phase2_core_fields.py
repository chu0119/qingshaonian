"""phase 2 core fields and external logs

Revision ID: 202605260002
Revises: 202605260001
Create Date: 2026-05-26 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260002"
down_revision: Union[str, None] = "202605260001"
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
    inspector = sa.inspect(op.get_bind())
    _add_column_if_missing("tasks", sa.Column("published_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("tasks", sa.Column("closed_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("tasks", sa.Column("extended_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("tasks", sa.Column("reminder_strategy", sa.JSON(), nullable=True))
    _add_column_if_missing("tasks", sa.Column("target_snapshot", sa.JSON(), nullable=True))
    _add_column_if_missing("tasks", sa.Column("description", sa.Text(), nullable=True))

    _add_column_if_missing("answer_sheets", sa.Column("school_id", sa.Integer(), nullable=True))
    _add_column_if_missing("answer_sheets", sa.Column("class_id", sa.Integer(), nullable=True))

    _add_column_if_missing("risk_alerts", sa.Column("due_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("risk_alerts", sa.Column("latest_handled_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("risk_alerts", sa.Column("closed_reason", sa.Text(), nullable=True))
    _add_column_if_missing("risk_alerts", sa.Column("source_rule_version", sa.String(length=50), nullable=True))

    _add_column_if_missing("interventions", sa.Column("follow_up_status", sa.String(length=20), nullable=True))
    _add_column_if_missing("interventions", sa.Column("closed_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("interventions", sa.Column("attachments", sa.JSON(), nullable=True))
    _add_column_if_missing("interventions", sa.Column("visibility_scope", sa.String(length=30), nullable=True))

    _add_column_if_missing("questionnaires", sa.Column("version", sa.Integer(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("locked_after_publish", sa.Boolean(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("source_questionnaire_id", sa.Integer(), nullable=True))
    _add_column_if_missing("questionnaires", sa.Column("rule_version", sa.String(length=50), nullable=True))

    if not inspector.has_table("sms_logs"):
        op.create_table(
            "sms_logs",
            sa.Column("recipient_user_id", sa.Integer(), nullable=True),
            sa.Column("recipient_name", sa.String(length=100), nullable=True),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("sms_type", sa.String(length=50), nullable=True),
            sa.Column("template_code", sa.String(length=100), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("sender_id", sa.Integer(), nullable=True),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("ai_analysis_logs"):
        op.create_table(
            "ai_analysis_logs",
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("user_role", sa.String(length=30), nullable=True),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("object_type", sa.String(length=50), nullable=True),
            sa.Column("object_id", sa.String(length=100), nullable=True),
            sa.Column("analysis_type", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("model_name", sa.String(length=100), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE tasks SET status = 'in_progress' WHERE status = 'active'"))
    bind.execute(sa.text("UPDATE tasks SET published_at = created_at WHERE published_at IS NULL AND status IN ('not_started','in_progress','ended','closed','archived')"))
    bind.execute(sa.text("UPDATE risk_alerts SET source_rule_version = 'v1' WHERE source_rule_version IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET version = 1 WHERE version IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET locked_after_publish = 0 WHERE locked_after_publish IS NULL"))
    bind.execute(sa.text("UPDATE questionnaires SET rule_version = 'v1' WHERE rule_version IS NULL"))


def downgrade() -> None:
    pass
