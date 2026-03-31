"""add client rsvp guests table

Revision ID: a8c9d0e1f2a3
Revises: f4c5d6e7f809
Create Date: 2026-02-26 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a8c9d0e1f2a3"
down_revision = "f4c5d6e7f809"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_rsvp_guests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("group_label", sa.String(length=80), nullable=True),
        sa.Column("table_name", sa.String(length=120), nullable=True),
        sa.Column("meal_choice", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_rsvp_guests_client_id"), "client_rsvp_guests", ["client_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_client_rsvp_guests_client_id"), table_name="client_rsvp_guests")
    op.drop_table("client_rsvp_guests")
