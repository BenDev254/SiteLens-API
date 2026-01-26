"""Add email to professional

Revision ID: b9a4a0e89095
Revises: 9b82aaf66885
Create Date: 2026-01-24 03:25:58.016362
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b9a4a0e89095'
down_revision = '9b82aaf66885'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add email column to professional using SQLAlchemy String type
    op.add_column('professional', sa.Column('email', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professional', 'email')
