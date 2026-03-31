"""add communications module tables

Revision ID: b1a2c3d4e5f6
Revises: a8c9d0e1f2a3
Create Date: 2026-02-26 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b1a2c3d4e5f6"
down_revision = "a8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("audience", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("subject_template", sa.String(length=255), nullable=False),
        sa.Column("body_html_template", sa.Text(), nullable=False),
        sa.Column("body_markdown_template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_email_templates_key"), "email_templates", ["key"], unique=True)

    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("trigger_type", sa.String(length=60), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("trigger_offset_days", sa.Integer(), nullable=True),
        sa.Column("trigger_offset_hours", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["email_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_automation_rules_key"), "automation_rules", ["key"], unique=True)
    op.create_index(op.f("ix_automation_rules_template_id"), "automation_rules", ["template_id"], unique=False)

    op.create_table(
        "communication_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("automation_rule_id", sa.Integer(), nullable=True),
        sa.Column("client_user_id", sa.Integer(), nullable=True),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column("vendor_booking_id", sa.Integer(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("trigger_source", sa.String(length=20), nullable=False),
        sa.Column("lifecycle_key", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=True),
        sa.Column("recipient_email", sa.String(length=180), nullable=False),
        sa.Column("sender_email", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_name", sa.String(length=30), nullable=True),
        sa.Column("provider_message_id", sa.String(length=180), nullable=True),
        sa.Column("provider_error", sa.Text(), nullable=True),
        sa.Column("subject_rendered", sa.String(length=255), nullable=False),
        sa.Column("body_html_rendered", sa.Text(), nullable=False),
        sa.Column("body_markdown_rendered", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["automation_rule_id"], ["automation_rules.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["booking_requests.id"]),
        sa.ForeignKeyConstraint(["client_user_id"], ["client_users.id"]),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["email_templates.id"]),
        sa.ForeignKeyConstraint(["vendor_booking_id"], ["vendor_bookings.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_communication_logs_automation_rule_id"), "communication_logs", ["automation_rule_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_booking_id"), "communication_logs", ["booking_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_client_user_id"), "communication_logs", ["client_user_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_created_by_admin_id"), "communication_logs", ["created_by_admin_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_idempotency_key"), "communication_logs", ["idempotency_key"], unique=True)
    op.create_index(op.f("ix_communication_logs_payment_id"), "communication_logs", ["payment_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_recipient_email"), "communication_logs", ["recipient_email"], unique=False)
    op.create_index(op.f("ix_communication_logs_scheduled_for"), "communication_logs", ["scheduled_for"], unique=False)
    op.create_index(op.f("ix_communication_logs_status"), "communication_logs", ["status"], unique=False)
    op.create_index(op.f("ix_communication_logs_template_id"), "communication_logs", ["template_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_vendor_booking_id"), "communication_logs", ["vendor_booking_id"], unique=False)
    op.create_index(op.f("ix_communication_logs_vendor_id"), "communication_logs", ["vendor_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_communication_logs_vendor_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_vendor_booking_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_template_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_status"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_scheduled_for"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_recipient_email"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_payment_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_idempotency_key"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_created_by_admin_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_client_user_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_booking_id"), table_name="communication_logs")
    op.drop_index(op.f("ix_communication_logs_automation_rule_id"), table_name="communication_logs")
    op.drop_table("communication_logs")

    op.drop_index(op.f("ix_automation_rules_template_id"), table_name="automation_rules")
    op.drop_index(op.f("ix_automation_rules_key"), table_name="automation_rules")
    op.drop_table("automation_rules")

    op.drop_index(op.f("ix_email_templates_key"), table_name="email_templates")
    op.drop_table("email_templates")
