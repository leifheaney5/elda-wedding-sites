"""add email subscribers table

Revision ID: f4c5d6e7f809
Revises: f3b4c5d6e7f8
Create Date: 2026-02-26 20:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f4c5d6e7f809"
down_revision = "f3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_subscribers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subscribed_at", sa.DateTime(), nullable=False),
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
        sa.Column("last_email_sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_email_subscribers_email"), "email_subscribers", ["email"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_email_subscribers_email"), table_name="email_subscribers")
    op.drop_table("email_subscribers")
