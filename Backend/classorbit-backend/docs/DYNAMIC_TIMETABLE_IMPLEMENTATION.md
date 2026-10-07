# Dynamic Timetable MVC Implementation

Date: 2026-09-21

## Result

ClassOrbit now derives timetable columns, printed time rows, page context, and cell boundaries from the incoming document. Class names remain data; they no longer select parser geometry. The normalized relational core remains intact, and controlled JSON fields preserve genuinely variable source metadata and entry attributes.

The pre-change evidence and cleanup decisions are in [DYNAMIC_TIMETABLE_AUDIT.md](DYNAMIC_TIMETABLE_AUDIT.md).

## Architecture

ClassOrbit follows an MVC-style modular architecture:

- **Model:** SQLAlchemy entities, normalized timetable relationships, Pydantic data contracts, and database migrations.
- **View:** React pages and components that render timetable structures returned by the API.
- **Controller:** FastAPI routers that validate requests, enforce authorization, invoke application services, and return responses.
- **Supporting services:** PDF extraction, timetable interpretation, validation, persistence, and reporting logic used by the controllers.

```text
React view
  -> FastAPI controller
  -> extraction/application services
  -> SQLAlchemy model and database

uploaded PDF
  -> PyMuPDF positioned words when available
     OR rendered page + Tesseract positioned words
  -> generic page header and grid analysis
  -> ordered detected column labels and printed time ranges
  -> raw cells with page/row/column/box/lines/context
  -> subject, room, category, session, delivery and attribute interpretation
  -> validation, deterministic confidence, duplicate analysis
  -> valid production records OR staged review records
  -> normalized database plus controlled metadata/attributes
  -> /api/timetable-structures
  -> source-driven React timetable grid
```

## Major Changes

### Extraction

- Replaced FYBA/FYBCom/FYBSc/department geometry selection with one `DETECTED_GRID_V2` strategy.
- Detected the header row from positioned weekday labels, inferred missing OCR weekday labels from source sequence/spacing, and retained a labelled extra column when present.
- Derived boundaries from header centers and snapped them to page line evidence.
- Derived rows from printed time tokens. When one page loses a token to OCR, source slots already detected on another page in the same document can reconstruct that page's row geometry; no fixed 07:15 schedule remains.
- Added generic labelled extraction for class, division/section, department, hall/room, semester, batch, group, faculty, course/program, and controlled unknown labels.
- New class and division values such as `New Integrated Programme` and `Alpha-2` require no parser change.
- Preserved raw cell lines and detected layout coordinates in trace metadata.
- Added image timetable OCR, DOCX table extraction, and visual Excel-grid extraction through the same normalized validation pipeline.
- Manual entry corrections remain traceable, while entries removed as `No activity` are retained as ignored review labels for future extraction evaluation or model training.

### Database

- `timetables.metadata_json`: ordered source columns, source time-slot order, hall/context attributes, and detected layout details.
- `import_reviews.attributes_json`: variable source fields while a record is staged.
- `timetable_entries.attributes_json`: validated variable fields such as batch/group/custom structured columns.
- Core class, department, division, subject, classroom, time slot, and entry relationships remain normalized.
- Alembic revision `20260921_02` adds and backfills the JSON fields. The complete migration chain was tested against an isolated legacy-style SQLite schema.

### API And UI

- Added `GET /api/timetable-structures` without removing existing timetable APIs.
- Each structure returns its timetable context, actual ordered columns, actual used slots, entries, and dynamic attribute keys.
- The React timetable page now builds selectors and grid columns from the response. It no longer declares Monday-Saturday or a fixed row count.
- Multiple entries remain visible within the same day/time cell. Session and delivery modes are displayed, and variable attributes become dynamic extracted-entry columns.
- Upload progress, classroom views, subjects, time slots, notifications, and legacy API consumers remain supported.

### Reliability And Reports

- Quality reports now include parser strategy, detected timetable contexts, recognized entities, dynamic attributes, and unique unknown/unclassified content.
- Schedule queries preserve custom source column labels when they are not standard weekdays.
- CSV/Excel imports retain unused named columns as controlled attributes and use the same validation/persistence path.

## Old Vs Dynamic Results

Counts are routing/coverage indicators, not proof that every OCR word is correct. Visual samples were checked for subject/room/time/context relationships.

| PDF | Old entries | Dynamic entries | Old valid | Dynamic valid | Dynamic review | Dynamic invalid |
|---|---:|---:|---:|---:|---:|---:|
| F.Y.B.A. | 204 | 207 | 200 | 203 | 0 | 4 |
| F.Y.B.Com | 93 | 88 | 85 | 81 | 7 | 0 |
| F.Y.BSc | 22 | 22 | 22 | 22 | 0 | 0 |
| S.Y.B.A. | 934 | 981 | 868 | 933 | 35 | 13 |
| T.Y.B.A. | 673 | 649 | 624 | 612 | 1 | 36 |

The dynamic detector extracted all 46 available pages. FYBA subject/room pairs such as `Hindi / CC 4`, inherited FYBCom/FYBSc halls, FYBSc noon rollover, department context, and TYBA Major/category handling remain structured. BCom and TYBA count differences reflect geometry/validation changes and OCR variation; uncertain text remains traceable rather than being silently promoted.

The machine-readable report is [extraction-quality-dynamic-2026-09-21.json](extraction-quality-dynamic-2026-09-21.json).

## Cleanup

Removed only reference-checked artifacts:

- accidental empty backend root file `3.2`
- manual `artifacts/*.png` inspection outputs and the empty folder
- superseded intermediate quality JSON files
- unused Vite starter assets `react.svg`, `vite.svg`, and unreferenced `hero.png`

No active backend module or dependency was removed. Runtime uploads, local databases, installed environments, authentication, schedule, allocation, CSV/Excel, and review code were retained.

## Verification

- Backend unit/API suite: all tests pass, including unseen classes, multi-character divisions, custom columns, dynamic structure responses, unknown attributes, import caching, quality, and trace behavior.
- Frontend: production build passes.
- Frontend: ESLint passes.
- Alembic revisions `20260921_01 -> 20260921_02` pass on an isolated legacy schema.
- No development server was started.

## Remaining Limits

- OCR spelling mistakes are preserved instead of being guessed away. Examples such as a lost initial letter or `!` replacing `I` can still require review.
- A page must expose enough line/header/time evidence to identify a timetable. Unrecognizable layouts remain reviewable raw extraction rather than fabricated schedule data.
- Standard weekday aliases receive canonical names. Arbitrary extra source columns are preserved, but unusual multi-row/merged headers may require another reusable layout-evidence rule.
- A separate FYBSc Microbiology PDF was not available. Microbiology entries in the supplied FYBSc file were tested, but an unavailable document layout is not claimed as verified.
- The system is deterministic and extensible, not a claim of 100% extraction accuracy.
