from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, allocations, auth, imports, master_data, schedule, timetables, users
from app.core.config import get_settings
from app.db.base import Base
from app.db.init_db import ensure_default_roles
from app.db.schema_upgrade import backfill_detected_time_slots, ensure_import_context_columns, normalize_timetable_time_slots
from app.db.session import SessionLocal, engine


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
        ensure_import_context_columns(engine)
        normalize_timetable_time_slots(engine)
        backfill_detected_time_slots(engine)
    db = SessionLocal()
    try:
        ensure_default_roles(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(master_data.router, prefix=settings.api_prefix)
app.include_router(timetables.router, prefix=settings.api_prefix)
app.include_router(allocations.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(schedule.router, prefix=settings.api_prefix)
