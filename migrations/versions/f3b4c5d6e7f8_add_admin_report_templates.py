"""add admin report templates

Revision ID: f3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-02-26 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_report_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dataset", sa.String(length=30), nullable=False),
        sa.Column("fields_csv", sa.Text(), nullable=False),
        sa.Column("status_filter", sa.String(length=30), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=True),
        sa.Column("date_end", sa.Date(), nullable=True),
        sa.Column("viz_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_report_templates_created_by_id"),
        "admin_report_templates",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_report_templates_dataset"),
        "admin_report_templates",
        ["dataset"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_admin_report_templates_dataset"), table_name="admin_report_templates")
    op.drop_index(op.f("ix_admin_report_templates_created_by_id"), table_name="admin_report_templates")
    op.drop_table("admin_report_templates")
