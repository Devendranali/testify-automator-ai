"""add uuid/display name/user story columns to test_case_metadata

Revision ID: 20260203_0012
Revises: 20251219_0011
Create Date: 2026-02-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import uuid

# revision identifiers, used by Alembic.
revision = "20260203_0012"
down_revision = "20251219_0011"
branch_labels = None
depends_on = None


def _generate_uuid():
    return str(uuid.uuid4())


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}

    if "case_uuid" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("case_uuid", sa.String(length=64), nullable=True),
        )
    if "display_name" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("display_name", sa.String(length=255), nullable=True),
        )
    if "user_story" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("user_story", sa.Text(), nullable=True),
        )
    if "auto_testcase" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("auto_testcase", sa.Text(), nullable=True),
        )
    if "test_type" not in columns:
        op.add_column(
            "test_case_metadata",
            sa.Column("test_type", sa.String(length=32), nullable=True),
        )

    conn = op.get_bind()
    records = conn.execute(text("SELECT id FROM test_case_metadata")).fetchall()
    for record in records:
        case_id = record[0]
        conn.execute(
            text(
                "UPDATE test_case_metadata SET case_uuid = :uuid, display_name = :name "
                "WHERE id = :id AND (case_uuid IS NULL OR case_uuid = '')"
            ),
            {
                "uuid": _generate_uuid(),
                "name": f"tc_{case_id}",
                "id": case_id,
            },
        )
        conn.execute(
            text(
                "UPDATE test_case_metadata SET user_story = '' "
                "WHERE id = :id AND (user_story IS NULL OR user_story = '')"
            ),
            {"id": case_id},
        )
        conn.execute(
            text(
                "UPDATE test_case_metadata SET auto_testcase = '' "
                "WHERE id = :id AND (auto_testcase IS NULL OR auto_testcase = '')"
            ),
            {"id": case_id},
        )
        conn.execute(
            text(
                "UPDATE test_case_metadata SET test_type = 'ui' "
                "WHERE id = :id AND (test_type IS NULL OR test_type = '')"
            ),
            {"id": case_id},
        )

    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    if "case_uuid" in columns:
        op.alter_column("test_case_metadata", "case_uuid", nullable=False)
        op.create_unique_constraint(
            "uq_test_case_metadata_case_uuid", "test_case_metadata", ["case_uuid"]
        )
    if "display_name" in columns:
        op.alter_column("test_case_metadata", "display_name", nullable=False)
        op.create_unique_constraint(
            "uq_test_case_metadata_project_display_name",
            "test_case_metadata",
            ["project_id", "display_name"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("test_case_metadata")}
    indexes = {idx["name"] for idx in inspector.get_indexes("test_case_metadata")}

    if "uq_test_case_metadata_case_uuid" in indexes:
        op.drop_constraint("uq_test_case_metadata_case_uuid", "test_case_metadata", type_="unique")
    if "uq_test_case_metadata_project_display_name" in indexes:
        op.drop_constraint(
            "uq_test_case_metadata_project_display_name", "test_case_metadata", type_="unique"
        )

    if "test_type" in columns:
        op.drop_column("test_case_metadata", "test_type")
    if "auto_testcase" in columns:
        op.drop_column("test_case_metadata", "auto_testcase")
    if "user_story" in columns:
        op.drop_column("test_case_metadata", "user_story")
    if "display_name" in columns:
        op.drop_column("test_case_metadata", "display_name")
    if "case_uuid" in columns:
        op.drop_column("test_case_metadata", "case_uuid")
