import uuid
from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.timetable import TimeSlot, Timetable
from app.utils.time_utils import parse_time_value, time_to_string


TIMETABLE_CONTEXT_CONSTRAINT = "uq_timetable_context_source"
TIMETABLE_CONTEXT_COLUMNS = [
    "academic_year",
    "class_name",
    "division",
    "semester",
    "department_id",
    "program_name",
    "source_import_id",
]


def ensure_import_context_columns(engine: Engine) -> None:
    """Add nullable import-context columns for databases created before this feature."""
    additions = {
        "file_imports": {
            "sha256": "VARCHAR(64)",
            "parser_version": "VARCHAR(32)",
        },
        "timetables": {
            "department_id": "VARCHAR(36)",
            "program_name": "VARCHAR(180)",
            "metadata_json": "JSON",
        },
        "import_reviews": {
            "source_sheet": "VARCHAR(120)",
            "department_name": "VARCHAR(180)",
            "program_name": "VARCHAR(180)",
            "subject_code": "VARCHAR(80)",
            "subject_type": "VARCHAR(80)",
            "session_type": "VARCHAR(80)",
            "delivery_mode": "VARCHAR(80)",
            "confidence_level": "VARCHAR(16)",
            "confidence_score": "FLOAT",
            "parser_name": "VARCHAR(120)",
            "template_name": "VARCHAR(120)",
            "extraction_method": "VARCHAR(80)",
            "bounding_box_json": "JSON",
            "attributes_json": "JSON",
        },
        "timetable_entries": {
            "source_sheet": "VARCHAR(120)",
            "subject_code": "VARCHAR(80)",
            "subject_type": "VARCHAR(80)",
            "session_type": "VARCHAR(80)",
            "delivery_mode": "VARCHAR(80)",
            "confidence_level": "VARCHAR(16)",
            "confidence_score": "FLOAT",
            "parser_name": "VARCHAR(120)",
            "template_name": "VARCHAR(120)",
            "extraction_method": "VARCHAR(80)",
            "bounding_box_json": "JSON",
            "trace_json": "JSON",
            "attributes_json": "JSON",
        },
    }
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, sql_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {sql_type}'))
        for table_name in ("import_reviews", "timetable_entries"):
            if table_name not in existing_tables:
                continue
            connection.execute(
                text(
                    f'UPDATE "{table_name}" SET "confidence_level" = \'MEDIUM\' '
                    'WHERE "confidence_level" IS NULL'
                )
            )
            connection.execute(
                text(f'UPDATE "{table_name}" SET "confidence_score" = 0 WHERE "confidence_score" IS NULL')
            )
        if "timetable_entries" in existing_tables:
            empty_json = "'{}'::json" if engine.dialect.name == "postgresql" else "'{}'"
            connection.execute(
                text(f'UPDATE "timetable_entries" SET "trace_json" = {empty_json} WHERE "trace_json" IS NULL')
            )
        empty_json = "'{}'::json" if engine.dialect.name == "postgresql" else "'{}'"
        for table_name, column_name in (
            ("timetables", "metadata_json"),
            ("import_reviews", "attributes_json"),
            ("timetable_entries", "attributes_json"),
        ):
            if table_name in existing_tables:
                connection.execute(
                    text(f'UPDATE "{table_name}" SET "{column_name}" = {empty_json} WHERE "{column_name}" IS NULL')
                )
    ensure_timetable_context_constraint(engine)


def ensure_timetable_context_constraint(engine: Engine) -> None:
    """Replace the legacy context constraint after department/program columns are added."""
    inspector = inspect(engine)
    if "timetables" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("timetables")}
    if not set(TIMETABLE_CONTEXT_COLUMNS).issubset(columns):
        return
    constraint = next(
        (
            item
            for item in inspector.get_unique_constraints("timetables")
            if item.get("name") == TIMETABLE_CONTEXT_CONSTRAINT
        ),
        None,
    )
    if constraint and constraint.get("column_names") == TIMETABLE_CONTEXT_COLUMNS:
        return

    if engine.dialect.name != "postgresql":
        # Fresh non-PostgreSQL databases receive the current constraint from metadata.
        return

    quoted_columns = ", ".join(f'"{column}"' for column in TIMETABLE_CONTEXT_COLUMNS)
    with engine.begin() as connection:
        connection.execute(
            text(f'ALTER TABLE "timetables" DROP CONSTRAINT IF EXISTS "{TIMETABLE_CONTEXT_CONSTRAINT}"')
        )
        connection.execute(
            text(
                f'ALTER TABLE "timetables" ADD CONSTRAINT "{TIMETABLE_CONTEXT_CONSTRAINT}" '
                f"UNIQUE ({quoted_columns})"
            )
        )


def normalize_timetable_time_slots(engine: Engine) -> None:
    """Backfill legacy timetable times into reusable time_slots rows."""
    inspector = inspect(engine)
    if "timetable_entries" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("timetable_entries")}
    if "start_time" not in columns or "end_time" not in columns:
        return

    dialect = engine.dialect.name
    with engine.begin() as connection:
        if "time_slot_id" not in columns:
            connection.execute(text('ALTER TABLE "timetable_entries" ADD COLUMN "time_slot_id" VARCHAR(36)'))

        ranges = connection.execute(
            text('SELECT DISTINCT "start_time", "end_time" FROM "timetable_entries"')
        ).all()
        for start_time, end_time in ranges:
            existing = connection.execute(
                text('SELECT "id" FROM "time_slots" WHERE "start_time" = :start AND "end_time" = :end'),
                {"start": start_time, "end": end_time},
            ).scalar_one_or_none()
            time_slot_id = existing or str(uuid.uuid4())
            if not existing:
                now = datetime.now(timezone.utc)
                connection.execute(
                    text(
                        'INSERT INTO "time_slots" '
                        '("id", "created_at", "updated_at", "start_time", "end_time") '
                        'VALUES (:id, :created, :updated, :start, :end)'
                    ),
                    {"id": time_slot_id, "created": now, "updated": now, "start": start_time, "end": end_time},
                )
            connection.execute(
                text(
                    'UPDATE "timetable_entries" SET "time_slot_id" = :slot_id '
                    'WHERE "start_time" = :start AND "end_time" = :end AND "time_slot_id" IS NULL'
                ),
                {"slot_id": time_slot_id, "start": start_time, "end": end_time},
            )

        missing = connection.execute(
            text('SELECT COUNT(*) FROM "timetable_entries" WHERE "time_slot_id" IS NULL')
        ).scalar_one()
        if missing:
            raise RuntimeError(f"Could not assign time slots to {missing} timetable entries.")

        if dialect == "postgresql":
            connection.execute(text('ALTER TABLE "timetable_entries" DROP CONSTRAINT IF EXISTS "uq_timetable_entry_source_identity"'))
            connection.execute(text('ALTER TABLE "timetable_entries" ALTER COLUMN "time_slot_id" SET NOT NULL'))
            connection.execute(
                text(
                    'ALTER TABLE "timetable_entries" ADD CONSTRAINT "fk_timetable_entries_time_slot_id" '
                    'FOREIGN KEY ("time_slot_id") REFERENCES "time_slots" ("id")'
                )
            )
            connection.execute(text('ALTER TABLE "timetable_entries" DROP COLUMN "start_time"'))
            connection.execute(text('ALTER TABLE "timetable_entries" DROP COLUMN "end_time"'))
            connection.execute(
                text(
                    'ALTER TABLE "timetable_entries" ADD CONSTRAINT "uq_timetable_entry_source_identity" '
                    'UNIQUE ("timetable_id", "day_of_week", "time_slot_id", "subject_text", '
                    '"room_hint", "raw_entry_text")'
                )
            )
            connection.execute(
                text('CREATE INDEX IF NOT EXISTS "ix_timetable_entries_time_slot_id" ON "timetable_entries" ("time_slot_id")')
            )


def backfill_detected_time_slots(engine: Engine) -> None:
    """Create reusable slots found in timetable metadata, including rows with no lectures."""
    inspector = inspect(engine)
    if not {"timetables", "time_slots"}.issubset(inspector.get_table_names()):
        return

    with Session(engine) as db:
        existing = {
            (time_to_string(slot.start_time), time_to_string(slot.end_time))
            for slot in db.query(TimeSlot).all()
        }
        for timetable in db.query(Timetable).all():
            for value in (timetable.metadata_json or {}).get("time_slot_order") or []:
                parts = value.split("-", maxsplit=1)
                if len(parts) != 2:
                    continue
                start_time = parse_time_value(parts[0])
                end_time = parse_time_value(parts[1])
                key = (time_to_string(start_time), time_to_string(end_time))
                if not start_time or not end_time or end_time <= start_time or key in existing:
                    continue
                db.add(TimeSlot(start_time=start_time, end_time=end_time))
                existing.add(key)
        db.commit()
