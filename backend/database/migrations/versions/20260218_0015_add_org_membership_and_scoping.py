"""add org membership table and enforce org scoping

Revision ID: 20260218_0015
Revises: 20260205_0014
Create Date: 2026-02-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_0015"
down_revision = "20260205_0014"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def _fk_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {fk["name"] for fk in inspector.get_foreign_keys(table_name)}


def _unique_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {uc["name"] for uc in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "org_members"):
        op.create_table(
            "org_members",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False, server_default="member"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_org_members_user_org"),
        )
        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "org_members", "ix_org_members_user_id"):
        op.create_index("ix_org_members_user_id", "org_members", ["user_id"], unique=False)
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "org_members", "ix_org_members_organization_id"):
        op.create_index("ix_org_members_organization_id", "org_members", ["organization_id"], unique=False)
        inspector = sa.inspect(bind)

    if not _fk_exists(inspector, "org_members", "fk_org_members_user_id"):
        op.create_foreign_key(
            "fk_org_members_user_id",
            "org_members",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        inspector = sa.inspect(bind)
    if not _fk_exists(inspector, "org_members", "fk_org_members_organization_id"):
        op.create_foreign_key(
            "fk_org_members_organization_id",
            "org_members",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        inspector = sa.inspect(bind)

    # Ensure projects.organization_id is indexed and non-null.
    if _table_exists(inspector, "projects") and not _index_exists(inspector, "projects", "ix_projects_organization_id"):
        op.create_index("ix_projects_organization_id", "projects", ["organization_id"], unique=False)
        inspector = sa.inspect(bind)
    if _table_exists(inspector, "projects"):
        cols = {col["name"]: col for col in inspector.get_columns("projects")}
        if "organization_id" in cols and cols["organization_id"].get("nullable", True):
            op.alter_column("projects", "organization_id", nullable=False)
            inspector = sa.inspect(bind)
        if not _fk_exists(inspector, "projects", "fk_projects_organization_id"):
            op.create_foreign_key(
                "fk_projects_organization_id",
                "projects",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # Backfill membership from users table.
    if _table_exists(inspector, "org_members") and _table_exists(inspector, "users"):
        bind.execute(
            sa.text(
                """
                INSERT INTO org_members (user_id, organization_id, role)
                SELECT u.id, u.organization_id, 'member'
                FROM users u
                WHERE u.organization_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM org_members m
                      WHERE m.user_id = u.id AND m.organization_id = u.organization_id
                  )
                """
            )
        )


def downgrade() -> None:
    op.drop_constraint("fk_org_members_organization_id", "org_members", type_="foreignkey")
    op.drop_constraint("fk_org_members_user_id", "org_members", type_="foreignkey")
    op.drop_index("ix_org_members_organization_id", table_name="org_members")
    op.drop_index("ix_org_members_user_id", table_name="org_members")
    op.drop_constraint("uq_org_members_user_org", "org_members", type_="unique")
    op.drop_table("org_members")

