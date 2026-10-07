"""Include department and program in timetable import identity.

Revision ID: 20261003_01
Revises: 20260928_01
Create Date: 2026-10-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261003_01"
down_revision = "20260928_01"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "uq_timetable_context_source"
CURRENT_COLUMNS = [
    "academic_year",
    "class_name",
    "division",
    "semester",
    "department_id",
    "program_name",
    "source_import_id",
]
LEGACY_COLUMNS = [
    "academic_year",
    "class_name",
    "division",
    "semester",
    "source_import_id",
]


def _replace_constraint(columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    constraints = {
        constraint.get("name"): constraint.get("column_names")
        for constraint in inspector.get_unique_constraints("timetables")
    }
    if constraints.get(CONSTRAINT_NAME) == columns:
        return
    with op.batch_alter_table("timetables") as batch_op:
        if CONSTRAINT_NAME in constraints:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")
        batch_op.create_unique_constraint(CONSTRAINT_NAME, columns)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "timetables" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("timetables")}
    if set(CURRENT_COLUMNS).issubset(existing_columns):
        _replace_constraint(CURRENT_COLUMNS)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "timetables" in inspector.get_table_names():
        _replace_constraint(LEGACY_COLUMNS)
