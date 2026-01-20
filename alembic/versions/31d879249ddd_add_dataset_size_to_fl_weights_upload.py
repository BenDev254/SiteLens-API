"""add dataset_size to fl_weights_upload

Revision ID: 31d879249ddd
Revises: fb455c038e94
Create Date: 2026-01-20 10:44:05.788860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31d879249ddd'
down_revision: Union[str, Sequence[str], None] = 'fb455c038e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add column with default for existing rows
    op.add_column(
        "fl_weights_upload",
        sa.Column("dataset_size", sa.Integer(), nullable=False, server_default="0")
    )

def downgrade():
    op.drop_column("fl_weights_upload", "dataset_size")
