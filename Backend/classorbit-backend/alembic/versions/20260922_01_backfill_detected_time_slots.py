"""Backfill detected empty timetable time slots.

Revision ID: 20260922_01
Revises: 20260921_02
Create Date: 2026-09-22
"""

from datetime import datetime, time, timezone
import json
import re
import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260922_01"
down_revision = "20260921_02"
branch_labels = None
depends_on = None


def _clock(value: str) -> time | None:
    match = re.fullmatch(r"\s*(\d{1,2})[.:](\d{2})\s*", value)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if 1 <= hour <= 6:
        hour += 12
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return time(hour, minute)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not {"timetables", "time_slots"}.issubset(inspector.get_table_names()):
        return

    time_slots = sa.table(
        "time_slots",
        sa.column("id", sa.String(36)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("start_time", sa.Time()),
        sa.column("end_time", sa.Time()),
    )

    existing = {
        (str(row.start_time)[:5], str(row.end_time)[:5])
        for row in bind.execute(sa.text('SELECT "start_time", "end_time" FROM "time_slots"'))
    }
    for row in bind.execute(sa.text('SELECT "metadata_json" FROM "timetables"')):
        metadata = row.metadata_json
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                continue
        for value in (metadata or {}).get("time_slot_order") or []:
            parts = value.split("-", maxsplit=1)
            if len(parts) != 2:
                continue
            start_time, end_time = _clock(parts[0]), _clock(parts[1])
            key = (
                start_time.strftime("%H:%M") if start_time else "",
                end_time.strftime("%H:%M") if end_time else "",
            )
            if not start_time or not end_time or end_time <= start_time or key in existing:
                continue
            now = datetime.now(timezone.utc)
            bind.execute(
                sa.insert(time_slots).values(
                    id=str(uuid.uuid4()),
                    created_at=now,
                    updated_at=now,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
            existing.add(key)


def downgrade() -> None:
    # Data-only migration: detected slots may now be referenced, so they are intentionally retained.
    pass
