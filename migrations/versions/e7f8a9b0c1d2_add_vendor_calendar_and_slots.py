"""add vendor calendar and slots

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-02-26 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vendor_calendar_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("external_calendar_id", sa.String(length=255), nullable=False),
        sa.Column("sync_direction", sa.String(length=20), nullable=False),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vendor_calendar_connections_vendor_id"),
        "vendor_calendar_connections",
        ["vendor_id"],
        unique=False,
    )

    op.create_table(
        "vendor_availability_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vendor_availability_slots_vendor_id"),
        "vendor_availability_slots",
        ["vendor_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_vendor_availability_slots_vendor_id"), table_name="vendor_availability_slots")
    op.drop_table("vendor_availability_slots")

    op.drop_index(op.f("ix_vendor_calendar_connections_vendor_id"), table_name="vendor_calendar_connections")
    op.drop_table("vendor_calendar_connections")
