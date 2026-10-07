# Dynamic Timetable System Audit

Date: 2026-09-21

## Scope

This audit describes the project after the first extraction-quality upgrade and before the dynamic-layout redesign. It covers the FastAPI backend, SQLAlchemy schema, parser/import services, migration strategy, React timetable integration, tests, generated artifacts, and all locally available timetable PDFs.

Runtime: Python 3.11.9, FastAPI, SQLAlchemy 2, Pydantic 2, PyMuPDF, Tesseract/pytesseract, Pillow, NumPy, pandas/openpyxl, PostgreSQL or SQLite, React 19, and Vite.

## Current Architecture

```text
POST /api/imports
  -> ImportService.create_import_from_upload
  -> SHA-256 upload reuse + FileImport
  -> parser factory (PDF, CSV, Excel)
  -> ParsedDocument / ParsedCell
  -> TimetableNormalizer
  -> TimetableValidator
  -> TimetableConfidenceScorer
  -> TimetableMapper
  -> ImportReview staging
  -> validated Timetable / TimeSlot / Subject / Classroom / TimetableEntry
  -> /api/timetables + /api/timetable-entries
  -> classOrbitApi.getTimetable
  -> React Timetable weekly grid and extracted-entry table
```

### Extraction ownership

| Stage | Current owner | Input | Output |
|---|---|---|---|
| Upload | `app/api/imports.py`, `ImportService.create_import_from_upload` | multipart file | stored file and `FileImport` |
| Parser selection | `app/parsers/factory.py` | file path | PDF/CSV/Excel parser |
| Native PDF/OCR | `app/parsers/pdf_parser.py` | PDF pages | positioned `OcrWord` pages |
| Layout | `pdf_parser._detect_grid`, `app/parsers/templates.py` | image projections plus selected class template | fixed-count vertical/horizontal boundaries |
| Context | `pdf_parser._detect_metadata` | flattened page/document text | metadata dictionary |
| Cells | `pdf_parser._cells_from_ocr` | words, grid, template | `ParsedCell` records |
| Interpretation | `TimetableNormalizer` | raw cell and inherited context | normalized entries |
| Trust | validator and confidence scorer | normalized entry | status, warning, confidence |
| Persistence | `ImportService.process_import` | validated/review entries | normalized core rows and review data |
| API | `app/api/timetables.py` | ORM rows | separate timetable and entry lists |
| Display | `classOrbitApi.getTimetable`, `AdminPages.jsx:Timetable` | joined client-side lists | fixed six-day weekly grid |

## What Works And Must Be Preserved

- Native coordinate words and OCR words enter the same parser path.
- OCR is a fallback for scanned PDFs.
- Raw cell text, source page/cell, bounding box, extraction method, parser identity, confidence, and decisions are retained.
- Subject and room are separate; uncertain records remain staged.
- Department and division are independent nullable context.
- Time slots, subjects, classrooms, timetables, and entries are normalized relational data.
- Core upload, review, confirmation, schedule, availability, subject, classroom, and time-slot APIs work.
- CSV/Excel use the same downstream normalization and validation path.
- Per-record savepoints prevent one bad cell from failing the whole import.
- Existing backend tests pass before this redesign.

## Confirmed Problems

### 1. Layout selection is class-driven

`app/parsers/templates.py:detect_template` explicitly searches for `FYBCOM`, `FYBSC`, and `Department`, then selects class-named geometry. A new class using the same geometry is not identified from its layout, while an existing class with a changed layout receives the wrong geometry.

Expected: select columns and rows from detected lines, labels, and coordinates. Geometry profiles may be generic fallbacks, never class rules.

### 2. Days are fixed in backend and frontend

`PdfTimetableParser.days`, every existing template, `_cells_from_ocr`, and `AdminPages.jsx` assume Monday through Saturday. The UI always renders six columns even when a source has fewer, more, or differently labelled columns.

Expected: detect header columns from the source, preserve their order/labels, expose them through a structure API, and render exactly those columns.

### 3. Row count and fallback times are fixed

Templates use `data_row_count=7`. `_times_for_row` fabricates a schedule beginning at 07:15 when printed times cannot be parsed.

Expected: use detected printed time ranges. Missing times must lower confidence or remain review data, never be invented.

### 4. Metadata extraction hardcodes class formats

`_detect_metadata` lists FY/SY/TY BA/BCom/BSc patterns and only permits one-letter divisions. New class names, multi-character sections, batches, groups, and new labelled fields are lost.

Expected: parse generic `Label: Value` header pairs, map known semantic label aliases, and retain unknown pairs in controlled metadata.

### 5. Variable context has no durable canonical home

Raw review JSON retains source rows and decisions, but `Timetable` has no metadata JSON and `TimetableEntry` has no controlled attributes JSON. Batch, group, section, teacher labels, or future fields cannot survive into a production timetable cleanly.

Expected: keep relational columns for core query fields and add metadata/attributes JSON for genuinely variable source fields.

### 6. Cell line geometry is discarded too early

`_words_in_box` turns positioned words into strings before normalization. `_combine_cell_lines` then uses trailing-room patterns and `/` separators. This handles current examples but cannot explain arbitrary subject/teacher/group alignment.

Expected: preserve detected lines and entity candidates in the raw cell trace/attributes while retaining conservative deterministic interpretation.

### 7. Unknown data is inconsistently retained

PDF unknown header labels are discarded. CSV/Excel preserve the complete source row under metadata, but only selected named columns are promoted.

Expected: unknown labelled metadata and unused structured columns remain available as unclassified attributes and are reported.

### 8. API does not return timetable structure

The frontend fetches all timetables, entries, and departments separately, joins them client-side, and derives time options. There is no response containing one timetable's ordered columns, ordered rows, context, dynamic attributes, and entries.

Expected: an additive structure endpoint assembled from stored data and source metadata.

### 9. Frontend display is structurally hardcoded

`AdminPages.jsx` declares `days = [Monday...Saturday]`, uses those values for filters and table columns, and mixes entries from multiple timetable contexts into one union grid.

Expected: select a timetable/context and render its returned ordered columns and slots. Entry chips may contain multiple entries for a source cell.

### 10. Subject interpretation remains regex-limited

The normalizer correctly separates current numeric/CC/AB room suffixes and category/delivery terms, but unknown room conventions, teachers, codes, batches, or groups remain in subject text or warnings.

Expected: composable entity candidates plus attributes; ambiguous tokens stay raw/review rather than polluting `Subject`.

### 11. Time-slot ordering is global, not source-specific

`TimeSlot` is appropriately deduplicated globally, but the current API does not preserve per-timetable row order or labels beyond chronological start/end.

Expected: structure responses derive only slots present in that timetable and order them from source position when available.

### 12. The first audit/report now describes superseded behavior

`TIMETABLE_EXTRACTION_AUDIT.md` is useful historical evidence but describes several issues already fixed. It must remain as history; this report is the current baseline.

### 13. Cleanup candidates are verified

- Backend root file `3.2` is an empty accidental artifact and has no references.
- `artifacts/*.png` are manual visual-inspection outputs, not runtime inputs.
- `docs/extraction-quality-compact-2026-09-21.json` and `docs/extraction-quality-foundation-2026-09-21.json` are intermediate reports superseded by the final report.
- Frontend `src/assets/react.svg`, `src/assets/vite.svg`, and `src/assets/hero.png` have no references.
- `__pycache__`, `.pytest_cache`, frontend `dist`, `node_modules`, backend `.venv`, uploaded source files, and the local database are generated/runtime state rather than source. They should stay ignored; local dependencies/uploads must not be deleted merely for tidiness.

No backend Python module or declared backend dependency is currently proven unused. Authentication, allocation, schedule, review, CSV, Excel, and master-data modules all have active imports or routes.

## MVC Dynamic Architecture

The system uses an MVC-style separation: SQLAlchemy entities and persistence form the Model, the React application is the View, and FastAPI routers are the Controller layer. Extraction, validation, and timetable services support the controllers without embedding presentation concerns.

```text
React view
  -> FastAPI controller
  -> timetable/extraction services
  -> SQLAlchemy model and database

PDF
  -> native positioned words OR OCR positioned words
  -> page projection/line analysis
  -> detected table rectangle and line clusters
  -> header-row cell labels and time-column detection
  -> ordered source columns and printed time rows
  -> generic labelled metadata + unknown label preservation
  -> raw cells with words, lines, box, row, column, context
  -> composable entity interpretation
  -> normalized core fields + controlled attributes
  -> validation/confidence/review
  -> normalized database + metadata/attribute JSON
  -> dynamic timetable structure API
  -> source-driven React grid
```

Fallback geometry will be based on observed line distributions and header labels, not class names. The source class value remains data only.

## Incremental Implementation Plan

1. Replace class templates with generic detected-layout contracts and projection-based grid detection.
2. Detect column labels and row times from each page; remove fabricated fixed schedules.
3. Replace class-name regex with generic labelled metadata extraction and unknown-field preservation.
4. Add timetable metadata and entry attributes as additive JSON columns with migration coverage.
5. Persist detected structure and unclassified attributes through review and production records.
6. Add an additive dynamic timetable-structure API.
7. Update only the timetable frontend workflow to consume source-driven columns/rows.
8. Remove only verified artifacts/dead assets.
9. Run unit/API/build checks and regenerate all real-PDF quality reports; visually compare samples.

## Compatibility Constraints

- Existing API routes and fields remain available.
- Existing historical records without dynamic metadata remain renderable from entry-derived structure.
- Core relational entities stay normalized; JSON is only for variable source metadata/attributes/layout order.
- Unknown data is retained but never silently promoted into trusted core fields.
- No backend or frontend server will be started during implementation.
