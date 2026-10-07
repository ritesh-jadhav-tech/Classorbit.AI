"""Add extraction provenance, semantics, and confidence fields.

Revision ID: 20260921_01
Revises:
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_01"
down_revision = None
branch_labels = None
depends_on = None


TABLE_COLUMNS = {
    "file_imports": {
        "sha256": sa.String(64),
        "parser_version": sa.String(32),
    },
    "timetables": {
        "department_id": sa.String(36),
        "program_name": sa.String(180),
    },
    "import_reviews": {
        "department_name": sa.String(180),
        "program_name": sa.String(180),
        "subject_code": sa.String(80),
        "subject_type": sa.String(80),
        "session_type": sa.String(80),
        "delivery_mode": sa.String(80),
        "confidence_level": sa.String(16),
        "confidence_score": sa.Float(),
        "parser_name": sa.String(120),
        "template_name": sa.String(120),
        "extraction_method": sa.String(80),
        "bounding_box_json": sa.JSON(),
    },
    "timetable_entries": {
        "subject_code": sa.String(80),
        "subject_type": sa.String(80),
        "session_type": sa.String(80),
        "delivery_mode": sa.String(80),
        "confidence_level": sa.String(16),
        "confidence_score": sa.Float(),
        "parser_name": sa.String(120),
        "template_name": sa.String(120),
        "extraction_method": sa.String(80),
        "bounding_box_json": sa.JSON(),
        "trace_json": sa.JSON(),
    },
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table_name, columns in TABLE_COLUMNS.items():
        if table_name not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for name, column_type in columns.items():
            if name not in existing:
                op.add_column(table_name, sa.Column(name, column_type, nullable=True))
        if table_name in {"import_reviews", "timetable_entries"}:
            op.execute(sa.text(f'UPDATE "{table_name}" SET confidence_level = \'MEDIUM\' WHERE confidence_level IS NULL'))
            op.execute(sa.text(f'UPDATE "{table_name}" SET confidence_score = 0 WHERE confidence_score IS NULL'))
    if "timetable_entries" in tables:
        op.execute(sa.text("UPDATE timetable_entries SET trace_json = '{}' WHERE trace_json IS NULL"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table_name, columns in TABLE_COLUMNS.items():
        if table_name not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for name in reversed(columns):
            if name in existing:
                op.drop_column(table_name, name)
