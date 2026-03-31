"""add site announcements

Revision ID: b7f1a2c9d4e5
Revises: f8b2c9d4a781
Create Date: 2026-02-25 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f1a2c9d4e5"
down_revision = "f8b2c9d4a781"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_site_announcements_created_by_id"),
        "site_announcements",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_site_announcements_is_active"),
        "site_announcements",
        ["is_active"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_site_announcements_is_active"), table_name="site_announcements")
    op.drop_index(op.f("ix_site_announcements_created_by_id"), table_name="site_announcements")
    op.drop_table("site_announcements")
