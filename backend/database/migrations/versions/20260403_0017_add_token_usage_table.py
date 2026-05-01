"""add token_usage table

Revision ID: 20260403_0017
Revises: 20260302_0016
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260403_0017"
down_revision = "20260302_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "token_usage" not in inspector.get_table_names():
        op.create_table(
            "token_usage",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("feature", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("cost", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("token_usage")}
    if "ix_token_usage_project_id" not in existing_indexes:
        op.create_index(
            "ix_token_usage_project_id",
            "token_usage",
            ["project_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_token_usage_project_id", table_name="token_usage")
    op.drop_table("token_usage")
