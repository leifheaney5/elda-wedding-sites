"""add vendor transactions

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-02-25 23:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vendor_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("milestone", sa.String(length=20), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("gross_cents", sa.Integer(), nullable=False),
        sa.Column("platform_fee_cents", sa.Integer(), nullable=False),
        sa.Column("vendor_net_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["vendor_bookings.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vendor_transactions_booking_id"),
        "vendor_transactions",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vendor_transactions_vendor_id"),
        "vendor_transactions",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vendor_transactions_stripe_payment_intent_id"),
        "vendor_transactions",
        ["stripe_payment_intent_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        op.f("ix_vendor_transactions_stripe_payment_intent_id"),
        table_name="vendor_transactions",
    )
    op.drop_index(op.f("ix_vendor_transactions_vendor_id"), table_name="vendor_transactions")
    op.drop_index(op.f("ix_vendor_transactions_booking_id"), table_name="vendor_transactions")
    op.drop_table("vendor_transactions")
