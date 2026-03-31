"""add client portal models and links

Revision ID: c5a2e4d7f1b8
Revises: 0a4c3af88ceb
Create Date: 2026-02-16 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c5a2e4d7f1b8"
down_revision = "0a4c3af88ceb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("auth_provider", sa.String(length=30), nullable=False),
        sa.Column("oauth_subject", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("oauth_subject"),
    )
    op.create_index(op.f("ix_client_users_email"), "client_users", ["email"], unique=True)

    op.add_column("booking_requests", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_booking_requests_client_id"), "booking_requests", ["client_id"], unique=False)
    op.create_foreign_key(
        "fk_booking_requests_client_id", "booking_requests", "client_users", ["client_id"], ["id"]
    )

    op.add_column("contact_submissions", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_contact_submissions_client_id"), "contact_submissions", ["client_id"], unique=False)
    op.create_foreign_key(
        "fk_contact_submissions_client_id", "contact_submissions", "client_users", ["client_id"], ["id"]
    )

    op.add_column("service_requests", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_service_requests_client_id"), "service_requests", ["client_id"], unique=False)
    op.create_foreign_key(
        "fk_service_requests_client_id", "service_requests", "client_users", ["client_id"], ["id"]
    )


def downgrade():
    op.drop_constraint("fk_service_requests_client_id", "service_requests", type_="foreignkey")
    op.drop_index(op.f("ix_service_requests_client_id"), table_name="service_requests")
    op.drop_column("service_requests", "client_id")

    op.drop_constraint("fk_contact_submissions_client_id", "contact_submissions", type_="foreignkey")
    op.drop_index(op.f("ix_contact_submissions_client_id"), table_name="contact_submissions")
    op.drop_column("contact_submissions", "client_id")

    op.drop_constraint("fk_booking_requests_client_id", "booking_requests", type_="foreignkey")
    op.drop_index(op.f("ix_booking_requests_client_id"), table_name="booking_requests")
    op.drop_column("booking_requests", "client_id")

    op.drop_index(op.f("ix_client_users_email"), table_name="client_users")
    op.drop_table("client_users")
