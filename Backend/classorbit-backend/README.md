# ClassOrbit Backend

FastAPI backend for the **AI-Based Classroom Occupancy and Smart Room Allocation System**.

This phase stores planned schedule data only. It does not implement CCTV, YOLO, or live occupancy detection.

## What Is Implemented

- JWT authentication with roles: `ADMIN`, `FACULTY`, `EXAM_COORDINATOR`
- Public role-based registration with immediate authentication token
- First-admin bootstrap endpoint
- Master data APIs for departments, faculty, subjects, buildings, floors, room types, and classrooms
- Timetable and classroom allocation APIs
- Reusable time-slot records referenced by timetable entries through `time_slot_id`
- Department-scoped subject records linked to every imported timetable entry
- Upload/import workflow for PDF, PNG/JPEG/TIFF/BMP/WebP images, DOCX, XLSX/XLSM/XLS, and CSV timetable files
- Deterministic ClassOrbit standard Excel import across every matching timetable sheet
- Conservative timetable normalization:
  - one source cell can create zero, one, or many review records
  - raw cell text and raw entry text are preserved
  - ambiguous room numbers are marked `NEEDS_REVIEW`
  - valid explicit room/lab values are matched or added to the classroom master
  - ambiguous and invalid room fragments remain in review
- Data-driven PDF extraction with coordinate words, scanned-page OCR fallback, detected columns, printed time rows, and no class-based geometry rules
- Dynamic timetable metadata and entry attributes for source fields such as batch, group, section, or future labelled values
- Per-entry parser provenance, bounding boxes, deterministic confidence, validation, and decision traces
- Import quality reports, review staging for uncertain records, semantic duplicate detection, and SHA-256 import reuse
- Admin review and confirmation APIs
- Schedule and availability APIs based on planned timetable/allocation data

## Run Locally

```bash
cd Backend/classorbit-backend
python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env

.venv\Scripts\activate

uvicorn app.main:app --reload
```

For quick local testing, you can leave `DATABASE_URL` unset and the app will use `sqlite:///./classorbit.db`.
For project deployment, set `DATABASE_URL` to PostgreSQL.

## First Admin

Create the first admin once:

```http
POST /api/auth/bootstrap-admin
{
  "name": "Admin User",
  "email": "admin@classorbit.edu",
  "password": "change-me-now"
}
```

After that, use:

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@classorbit.edu&password=change-me-now
```

## Register And Authenticate A User

Public registration accepts `ADMIN`, `FACULTY`, or `EXAM_COORDINATOR` and returns an access token:

```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "Faculty User",
  "email": "faculty@classorbit.edu",
  "password": "1234",
  "role": "FACULTY"
}
```

Use the returned token on protected endpoints:

```http
GET /api/auth/me
Authorization: Bearer <token>
```

For this testing phase, `/api/auth/register` allows all roles without authentication. Restrict admin and coordinator registration before production deployment. Admins can also create users through `POST /api/users`.

Passwords may contain 1 to 1024 characters during this testing phase. Restore a stronger minimum-password policy before production deployment.

## Timetable Import

### Preferred ClassOrbit Template

The supplied `ClassOrbit_Timetable_Template.xlsx` is the canonical format. Its single `Timetable Template` sheet contains metadata above a Monday-Saturday grid, with adjacent `Lecture / Subject` and `Classroom / Lab` columns under each day. Detection uses these workbook markers rather than the filename.

The parser reads every valid range in the `Time Slot` column, including custom rows added below the printed periods. Blank subject/room pairs remain empty display cells. A missing room uses the optional common hall; room-only cells, malformed times, missing metadata, multiple activities, unknown rooms, duplicates, and schedule conflicts remain in review.

Every supported format uses the same import pipeline. Valid entries are published immediately, while ambiguous or invalid records remain available in the review workflow. A clear physical room or lab value on a valid activity is matched or created in the classroom master. Set `CREATE_MISSING_CLASSROOMS_FROM_IMPORT=false` to require manual room mapping instead. The general `/api/imports` endpoint automatically selects the ClassOrbit workbook parser or the generic PDF, image, Excel, DOCX, and CSV parser as appropriate.

Excel visual grids inherit class, department, academic year, semester, division, and default-room values from label/value metadata above each table; lecture rows do not need to repeat those fields. Multiple tables and sheets remain separate schedule contexts. Named lab sections and locations such as `Pixel Lab`, `In Department`, or `In Music Department` are mapped to Laboratory classroom records owned by the relevant department.

Upload a timetable:

```http
POST /api/imports
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<PDF/IMAGE/DOCX/XLSX/XLSM/XLS/CSV>
```

Review parsed records:

```http
GET /api/imports/{import_id}/review
```

Inspect extraction quality and parser decisions:

```http
GET /api/imports/{import_id}/quality-report
GET /api/imports/{import_id}/trace?limit=100
```

Valid records are persisted immediately. Medium/low-confidence or ambiguous records remain in `import_reviews` until confirmed; invalid fragments such as headers, room-only values, and `-` placeholders never enter production timetable entries.

Confirm approved records:

```http
POST /api/imports/{import_id}/confirm
```

Imported intervals are deduplicated in `time_slots`; `timetable_entries` stores a `time_slot_id` instead of repeated start/end columns. Subject master records are also reused by canonical name and department while `subject_text` preserves the exact lecture label printed in the source.

Fetch complete source-driven timetable structures:

```http
GET /api/timetable-structures
```

Each result contains timetable context, the ordered columns actually detected, time slots present in that timetable, entries, and available dynamic attribute keys. Existing `/api/timetables` and `/api/timetable-entries` routes remain supported.

Generate a standalone report without importing into the database:

```bash
.venv\Scripts\python.exe scripts\run_extraction_quality.py path\to\timetable.pdf --output docs\quality.json
```

The current audit is in [`docs/DYNAMIC_TIMETABLE_AUDIT.md`](docs/DYNAMIC_TIMETABLE_AUDIT.md). The current implementation and real-PDF comparison are in [`docs/DYNAMIC_TIMETABLE_IMPLEMENTATION.md`](docs/DYNAMIC_TIMETABLE_IMPLEMENTATION.md). Earlier reports remain as project history.

```http
GET /api/time-slots
POST /api/time-slots
GET /api/subjects
```

## Query Schedule

```http
GET /api/schedule/by-room?room=414&day=Monday&time=09:15
GET /api/schedule/by-class?class_name=FYBA&division=A&day=Monday
GET /api/availability?room=414&day=Monday&start_time=11:15&end_time=12:15
```

Results are scheduled status only. They do not represent actual live occupancy.

## Scanned PDFs

The provided FYBA PDF has no readable text layer in PyMuPDF, so the importer uses Tesseract OCR. On Windows, the standard `C:/Program Files/Tesseract-OCR/tesseract.exe` location is detected automatically. For another location, set `TESSERACT_CMD` in `.env`.

Image uploads use the same positioned OCR and detected-grid pipeline. DOCX tables and visual Excel grids use a shared matrix detector; named-row Excel/CSV exports continue through the structured parser. Legacy binary `.doc` files must be saved as `.docx` before upload.

No OCR or learned model can guarantee exact output for every scan. ClassOrbit therefore preserves source text and coordinates, stages uncertain records for review, records manual corrections, and labels entries removed as extraction noise. These labels can be exported into a future project-specific training/evaluation dataset.

## Architecture

ClassOrbit follows an MVC-style separation across the complete application:

- **Model:** SQLAlchemy entities in `app/models/` and Pydantic contracts in `app/schemas/`
- **Controller:** thin authenticated HTTP handlers in `app/api/`
- **View:** the React application in `Frontend/smart-classroom/`
- **Service layer:** parsing, normalization, mapping, validation, imports, and schedule rules in `app/services/` and `app/parsers/`

API controllers do not contain timetable extraction or classroom-mapping rules.

```text
upload -> positioned PDF words or OCR words -> detected grid/headers/times
       -> raw cells -> normalization -> validation/confidence/review
       -> relational timetable data + controlled dynamic attributes
       -> REST structure API -> source-driven frontend grid
```

Core query concepts remain relational: `Timetable`, `Department`, `Subject`, `Classroom`, `TimeSlot`, and `TimetableEntry`. `Timetable.metadata_json` stores detected source structure and document-specific context. `TimetableEntry.attributes_json` stores genuinely variable entry fields without turning the database into a JSON-only design.

Relevant backend ownership:

- `app/parsers/`: file detection, coordinate/OCR extraction, and page layout detection
- `app/services/timetable_normalizer.py`: subject, room, type, mode, and dynamic attribute interpretation
- `app/services/timetable_validator.py` and `timetable_confidence.py`: trust boundary
- `app/services/import_service.py`: review staging and normalized persistence
- `app/api/timetables.py`: legacy list APIs and dynamic structure API
- `alembic/versions/`: production schema upgrades

## New Parsing Behavior

Do not add rules based on a class name. Extend reusable evidence detection instead:

1. Add semantic label aliases in `PdfTimetableParser._detect_metadata` only when the label has general meaning.
2. Extend positioned header/grid detection for a genuinely new layout characteristic.
3. Preserve unknown labelled values in `attributes` and raw trace data.
4. Add focused parser tests and run the quality script against every available PDF.
5. Keep uncertain interpretation in `import_reviews`; never silently create trusted master data.

## Debugging

Use `/api/imports/{id}/quality-report` for counts, detected structure, entities, unknown content, and warnings. Use `/api/imports/{id}/trace` to inspect bounding boxes, raw text, parser decisions, normalized values, confidence, and validation. For parser-only investigation, run `scripts/run_extraction_quality.py`; it does not write timetable records to the database.
