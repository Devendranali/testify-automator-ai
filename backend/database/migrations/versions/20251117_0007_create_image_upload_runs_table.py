"""create image_upload_runs table

Revision ID: 20251117_0007
Revises: 20251117_0006
Create Date: 2025-11-17 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251117_0007"
down_revision = "20251117_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_upload_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_upload_runs_project_id", "image_upload_runs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_image_upload_runs_project_id", table_name="image_upload_runs")
    op.drop_table("image_upload_runs")
