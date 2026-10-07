"""Add source-sheet trace fields for deterministic workbook imports.

Revision ID: 20260928_01
Revises: 20260922_01
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260928_01"
down_revision = "20260922_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("import_reviews", "timetable_entries"):
        if table_name not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if "source_sheet" not in existing:
            op.add_column(table_name, sa.Column("source_sheet", sa.String(length=120), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("timetable_entries", "import_reviews"):
        if table_name not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if "source_sheet" in existing:
            op.drop_column(table_name, "source_sheet")
