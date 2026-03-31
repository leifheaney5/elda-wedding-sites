"""add contact attachments for portal messages

Revision ID: e61c9c2e30ad
Revises: d2e9bf880c31
Create Date: 2026-02-17 01:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e61c9c2e30ad"
down_revision = "d2e9bf880c31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contact_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["submission_id"], ["contact_submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contact_attachments_submission_id"),
        "contact_attachments",
        ["submission_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_contact_attachments_submission_id"), table_name="contact_attachments"
    )
    op.drop_table("contact_attachments")
