"""add admin automation config

Revision ID: f2a3b4c5d6e7
Revises: f1c2d3e4a5b6
Create Date: 2026-02-26 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "f1c2d3e4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_automation_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("auto_mark_stale_bookings_reviewing", sa.Boolean(), nullable=False),
        sa.Column("stale_booking_days", sa.Integer(), nullable=False),
        sa.Column("unread_contacts_threshold", sa.Integer(), nullable=False),
        sa.Column("open_service_requests_threshold", sa.Integer(), nullable=False),
        sa.Column("pending_payments_threshold", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_summary", sa.Text(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_automation_configs_updated_by_id"),
        "admin_automation_configs",
        ["updated_by_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_admin_automation_configs_updated_by_id"),
        table_name="admin_automation_configs",
    )
    op.drop_table("admin_automation_configs")
