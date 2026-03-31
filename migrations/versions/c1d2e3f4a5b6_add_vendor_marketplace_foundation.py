"""add vendor marketplace foundation

Revision ID: c1d2e3f4a5b6
Revises: b7f1a2c9d4e5
Create Date: 2026-02-25 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b7f1a2c9d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("business_name", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendors_slug"), "vendors", ["slug"], unique=True)

    op.create_table(
        "vendor_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("permissions_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor_id", "admin_user_id", name="uq_vendor_membership"),
    )
    op.create_index(op.f("ix_vendor_memberships_vendor_id"), "vendor_memberships", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_vendor_memberships_admin_user_id"), "vendor_memberships", ["admin_user_id"], unique=False)

    op.create_table(
        "vendor_payout_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("stripe_account_id", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False),
        sa.Column("charges_enabled", sa.Boolean(), nullable=False),
        sa.Column("payouts_enabled", sa.Boolean(), nullable=False),
        sa.Column("onboarding_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_payout_accounts_vendor_id"), "vendor_payout_accounts", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_vendor_payout_accounts_stripe_account_id"), "vendor_payout_accounts", ["stripe_account_id"], unique=True)

    op.create_table(
        "vendor_packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_packages_vendor_id"), "vendor_packages", ["vendor_id"], unique=False)

    op.create_table(
        "vendor_package_addons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("is_optional", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["package_id"], ["vendor_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_package_addons_package_id"), "vendor_package_addons", ["package_id"], unique=False)

    op.create_table(
        "vendor_availability_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("min_lead_days", sa.Integer(), nullable=False),
        sa.Column("max_advance_days", sa.Integer(), nullable=False),
        sa.Column("blackout_dates_json", sa.JSON(), nullable=True),
        sa.Column("weekly_hours_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_availability_rules_vendor_id"), "vendor_availability_rules", ["vendor_id"], unique=True)

    op.create_table(
        "vendor_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("inquiry_name", sa.String(length=150), nullable=False),
        sa.Column("inquiry_email", sa.String(length=150), nullable=False),
        sa.Column("inquiry_phone", sa.String(length=30), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_leads_vendor_id"), "vendor_leads", ["vendor_id"], unique=False)

    op.create_table(
        "vendor_quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=True),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("tax_cents", sa.Integer(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["vendor_leads.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["vendor_packages.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_quotes_vendor_id"), "vendor_quotes", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_vendor_quotes_lead_id"), "vendor_quotes", ["lead_id"], unique=False)
    op.create_index(op.f("ix_vendor_quotes_package_id"), "vendor_quotes", ["package_id"], unique=False)

    op.create_table(
        "vendor_quote_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("total_price_cents", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["vendor_quotes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_quote_line_items_quote_id"), "vendor_quote_line_items", ["quote_id"], unique=False)

    op.create_table(
        "vendor_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("event_start_at", sa.DateTime(), nullable=True),
        sa.Column("event_end_at", sa.DateTime(), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["vendor_leads.id"]),
        sa.ForeignKeyConstraint(["quote_id"], ["vendor_quotes.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_bookings_vendor_id"), "vendor_bookings", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_vendor_bookings_lead_id"), "vendor_bookings", ["lead_id"], unique=False)
    op.create_index(op.f("ix_vendor_bookings_quote_id"), "vendor_bookings", ["quote_id"], unique=False)

    op.create_table(
        "vendor_payment_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("deposit_due_at", sa.DateTime(), nullable=True),
        sa.Column("deposit_amount_cents", sa.Integer(), nullable=False),
        sa.Column("final_due_at", sa.DateTime(), nullable=True),
        sa.Column("final_amount_cents", sa.Integer(), nullable=False),
        sa.Column("auto_schedule_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["vendor_bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendor_payment_plans_booking_id"), "vendor_payment_plans", ["booking_id"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_vendor_payment_plans_booking_id"), table_name="vendor_payment_plans")
    op.drop_table("vendor_payment_plans")

    op.drop_index(op.f("ix_vendor_bookings_quote_id"), table_name="vendor_bookings")
    op.drop_index(op.f("ix_vendor_bookings_lead_id"), table_name="vendor_bookings")
    op.drop_index(op.f("ix_vendor_bookings_vendor_id"), table_name="vendor_bookings")
    op.drop_table("vendor_bookings")

    op.drop_index(op.f("ix_vendor_quote_line_items_quote_id"), table_name="vendor_quote_line_items")
    op.drop_table("vendor_quote_line_items")

    op.drop_index(op.f("ix_vendor_quotes_package_id"), table_name="vendor_quotes")
    op.drop_index(op.f("ix_vendor_quotes_lead_id"), table_name="vendor_quotes")
    op.drop_index(op.f("ix_vendor_quotes_vendor_id"), table_name="vendor_quotes")
    op.drop_table("vendor_quotes")

    op.drop_index(op.f("ix_vendor_leads_vendor_id"), table_name="vendor_leads")
    op.drop_table("vendor_leads")

    op.drop_index(op.f("ix_vendor_availability_rules_vendor_id"), table_name="vendor_availability_rules")
    op.drop_table("vendor_availability_rules")

    op.drop_index(op.f("ix_vendor_package_addons_package_id"), table_name="vendor_package_addons")
    op.drop_table("vendor_package_addons")

    op.drop_index(op.f("ix_vendor_packages_vendor_id"), table_name="vendor_packages")
    op.drop_table("vendor_packages")

    op.drop_index(op.f("ix_vendor_payout_accounts_stripe_account_id"), table_name="vendor_payout_accounts")
    op.drop_index(op.f("ix_vendor_payout_accounts_vendor_id"), table_name="vendor_payout_accounts")
    op.drop_table("vendor_payout_accounts")

    op.drop_index(op.f("ix_vendor_memberships_admin_user_id"), table_name="vendor_memberships")
    op.drop_index(op.f("ix_vendor_memberships_vendor_id"), table_name="vendor_memberships")
    op.drop_table("vendor_memberships")

    op.drop_index(op.f("ix_vendors_slug"), table_name="vendors")
    op.drop_table("vendors")
