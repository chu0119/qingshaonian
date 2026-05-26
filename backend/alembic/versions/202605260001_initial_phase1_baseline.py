"""initial phase 1 baseline

Revision ID: 202605260001
Revises:
Create Date: 2026-05-26 00:00:00
"""
from typing import Sequence, Union

from alembic import op

from app.models.base import Base
from app.models import audit  # noqa: F401
from app.models import questionnaire  # noqa: F401
from app.models import risk  # noqa: F401
from app.models import system_config  # noqa: F401
from app.models import task  # noqa: F401
from app.models import user  # noqa: F401

revision: str = "202605260001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Initial baseline downgrade intentionally avoids dropping business data.
    pass
