"""add planning templates submissions and seating

Revision ID: f8b2c9d4a781
Revises: e61c9c2e30ad
Create Date: 2026-02-17 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f8b2c9d4a781"
down_revision = "e61c9c2e30ad"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planning_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("audience", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_planning_templates_template_key"),
        "planning_templates",
        ["template_key"],
        unique=True,
    )

    op.create_table(
        "seating_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("venue_area", sa.String(length=120), nullable=True),
        sa.Column("table_layout_json", sa.JSON(), nullable=True),
        sa.Column("rsvp_json", sa.JSON(), nullable=True),
        sa.Column("final_guest_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["booking_requests.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["client_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_seating_plans_booking_id"), "seating_plans", ["booking_id"], unique=False
    )
    op.create_index(
        op.f("ix_seating_plans_client_id"), "seating_plans", ["client_id"], unique=False
    )

    op.create_table(
        "planning_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("recipient_name", sa.String(length=150), nullable=True),
        sa.Column("recipient_email", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("rendered_text", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["booking_requests.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["client_users.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["planning_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_planning_submissions_booking_id"),
        "planning_submissions",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_planning_submissions_client_id"),
        "planning_submissions",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_planning_submissions_recipient_email"),
        "planning_submissions",
        ["recipient_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_planning_submissions_template_id"),
        "planning_submissions",
        ["template_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_planning_submissions_template_id"), table_name="planning_submissions")
    op.drop_index(op.f("ix_planning_submissions_recipient_email"), table_name="planning_submissions")
    op.drop_index(op.f("ix_planning_submissions_client_id"), table_name="planning_submissions")
    op.drop_index(op.f("ix_planning_submissions_booking_id"), table_name="planning_submissions")
    op.drop_table("planning_submissions")

    op.drop_index(op.f("ix_seating_plans_client_id"), table_name="seating_plans")
    op.drop_index(op.f("ix_seating_plans_booking_id"), table_name="seating_plans")
    op.drop_table("seating_plans")

    op.drop_index(op.f("ix_planning_templates_template_key"), table_name="planning_templates")
    op.drop_table("planning_templates")
