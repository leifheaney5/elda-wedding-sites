"""add client inspiration and plan tasks

Revision ID: d2e9bf880c31
Revises: c5a2e4d7f1b8
Create Date: 2026-02-16 21:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2e9bf880c31"
down_revision = "c5a2e4d7f1b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_inspirations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("colors", sa.String(length=500), nullable=True),
        sa.Column("themes", sa.String(length=500), nullable=True),
        sa.Column("florals", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["client_users.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index(
        op.f("ix_client_inspirations_client_id"),
        "client_inspirations",
        ["client_id"],
        unique=True,
    )

    op.create_table(
        "client_plan_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["client_users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_client_plan_tasks_client_id"),
        "client_plan_tasks",
        ["client_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_client_plan_tasks_client_id"), table_name="client_plan_tasks")
    op.drop_table("client_plan_tasks")
    op.drop_index(
        op.f("ix_client_inspirations_client_id"), table_name="client_inspirations"
    )
    op.drop_table("client_inspirations")
