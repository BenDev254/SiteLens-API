"""add email to users

Revision ID: 968d3dc890c0
Revises: b9a4a0e89095
Create Date: 2026-01-26 02:22:07.962106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '968d3dc890c0'
down_revision: Union[str, Sequence[str], None] = 'b9a4a0e89095'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as NULLABLE
    op.add_column(
        "users",
        sa.Column("email", sa.String(), nullable=True)
    )

    # 2. Add unique index (allows multiple NULLs in Postgres)
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
