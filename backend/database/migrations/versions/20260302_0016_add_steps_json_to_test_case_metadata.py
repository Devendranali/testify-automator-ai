"""add steps_json to test_case_metadata

Revision ID: 20260302_0016
Revises: 20260218_0015
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_0016"
down_revision = "20260218_0015"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    if "steps_json" not in columns:
        op.add_column("test_case_metadata", sa.Column("steps_json", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    if "steps_json" in columns:
        op.drop_column("test_case_metadata", "steps_json")
