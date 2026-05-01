"""add script_path column to test_case_metadata"""

from alembic import op
import sqlalchemy as sa

revision = "20260204_0013"
down_revision = "20260203_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_case_metadata",
        sa.Column("script_path", sa.String(length=1024), nullable=True),
    )
    op.create_index(
        "ix_test_case_metadata_script_path",
        "test_case_metadata",
        ["script_path"],
    )


def downgrade() -> None:
    op.drop_index("ix_test_case_metadata_script_path", table_name="test_case_metadata")
    op.drop_column("test_case_metadata", "script_path")
