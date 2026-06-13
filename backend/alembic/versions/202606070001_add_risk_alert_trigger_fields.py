"""add risk_alert trigger_method and trigger_detail

Revision ID: 202606070001
Revises: 202606010005
Create Date: 2026-06-07 10:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202606070001"
down_revision: Union[str, None] = "202606010005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # risk_alerts 表添加 trigger_method 和 trigger_detail 列
    op.add_column('risk_alerts', sa.Column('trigger_method', sa.String(50), server_default='total_score'))
    op.add_column('risk_alerts', sa.Column('trigger_detail', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('risk_alerts', 'trigger_detail')
    op.drop_column('risk_alerts', 'trigger_method')
