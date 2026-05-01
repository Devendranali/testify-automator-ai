"""add runner_script_path column to test_case_metadata"""

from alembic import op
import sqlalchemy as sa

revision = "20260205_0014"
down_revision = "20260204_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    if "runner_script_path" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("runner_script_path", sa.String(length=1024), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    if "runner_script_path" in columns:
        op.drop_column("test_case_metadata", "runner_script_path")
