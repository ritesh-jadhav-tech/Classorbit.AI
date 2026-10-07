"""Add dynamic timetable metadata and entry attributes.

Revision ID: 20260921_02
Revises: 20260921_01
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_02"
down_revision = "20260921_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    additions = {
        "timetables": ("metadata_json", sa.JSON()),
        "import_reviews": ("attributes_json", sa.JSON()),
        "timetable_entries": ("attributes_json", sa.JSON()),
    }
    for table_name, (column_name, column_type) in additions.items():
        if table_name not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name not in existing:
            op.add_column(table_name, sa.Column(column_name, column_type, nullable=True))
        op.execute(sa.text(f'UPDATE "{table_name}" SET "{column_name}" = \'{{}}\' WHERE "{column_name}" IS NULL'))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name, column_name in (
        ("timetables", "metadata_json"),
        ("import_reviews", "attributes_json"),
        ("timetable_entries", "attributes_json"),
    ):
        if table_name not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name in existing:
            op.drop_column(table_name, column_name)
