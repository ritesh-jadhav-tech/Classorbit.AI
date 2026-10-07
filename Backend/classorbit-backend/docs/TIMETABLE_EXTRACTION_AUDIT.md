# Timetable Extraction System Audit

Date: 2026-09-21

## Scope And Evidence

This audit covers the current FastAPI backend, parser implementations, import/review services, SQLAlchemy models, API contracts, frontend timetable integration, automated tests, the configured PostgreSQL data, and the timetable PDFs currently available locally.

Available real PDF formats:

- FYBA, 4 pages
- FYBCom, 4 pages
- SYBA, 18 pages
- TYBA, 18 pages
- FYBSc (available in Downloads but not yet imported/tested)

No FYBSc Microbiology PDF is currently available, so that format is not claimed as tested.

Runtime and dependencies:

- Python 3.11.9
- FastAPI, SQLAlchemy 2, Pydantic 2, PostgreSQL/psycopg
- PyMuPDF for PDF access/rendering
- Tesseract through pytesseract for scanned PDFs
- Pillow and NumPy for rendered-page/grid processing
- pandas/openpyxl for spreadsheets
- pytest/httpx for API tests

Tesseract is installed at a standard Windows location and is found by `PdfTimetableParser._find_tesseract`; it is not on the process `PATH`, so direct pytesseract calls without that configuration fail.

## Current Extraction Pipeline

```text
Upload API
  app/api/imports.py:upload_import
    -> app/services/import_service.py:ImportService.create_import_from_upload
      -> stored upload + FileImport row
      -> ImportService.process_import
        -> app/parsers/factory.py:get_parser_for_file
        -> PDF / CSV / Excel parser
        -> ParsedDocument containing ParsedCell objects
        -> TimetableNormalizer.normalize_cell
        -> TimetableValidator.validate
        -> TimetableMapper.map_classroom
        -> ImportReview row
        -> Timetable / TimeSlot / Subject / TimetableEntry / ClassroomAllocation rows
```

### PDF extraction

`app/parsers/pdf_parser.py:PdfTimetableParser.parse` first asks PyMuPDF for page text. If any usable page text exists, `_cells_from_text` uses flattened text and regex fragments. If the document has no text layer, `_ocr_pages` renders every page at 3x resolution and calls Tesseract `--psm 11`, preserving word coordinates temporarily in `OcrWord`.

For OCR pages, `_detect_grid` finds image lines, `_cells_from_ocr` assigns six fixed weekday columns and seven fixed timetable rows, and `_words_in_box` groups OCR words into cell lines. `_combine_cell_lines` attempts to split multiple subject/room pairs before emitting a `ParsedCell`.

### Interpretation and normalization

`app/services/timetable_normalizer.py:TimetableNormalizer` splits a cell on `/`, inherits page/document metadata, parses time values, separates selected trailing room patterns, and assigns a `LocationType`. `TimetableValidator` checks class, day, time ordering, and non-empty subject text. `TimetableMapper` finds or automatically creates a classroom for a parsed room hint.

### CSV and Excel

`CsvTimetableParser` and `ExcelTimetableParser` read named columns into the same `ParsedCell` contract. They preserve the input row in `metadata`, but do not share a formal extraction-method or confidence contract with PDF parsing.

## Current Database Flow

```text
ParsedCell
  -> NormalizedTimetableEntry (in memory)
  -> ImportReview (raw + interpreted review record)
  -> Timetable (class/context/source)
  -> TimeSlot (deduplicated start/end)
  -> Department and Subject master records
  -> Classroom master record when a room hint exists
  -> TimetableEntry
  -> ClassroomAllocation when a classroom is mapped
```

Important current behavior:

- `VALID` records are persisted immediately.
- `NEEDS_REVIEW` records are also persisted immediately into production `timetable_entries`.
- `INVALID` records remain only in `import_reviews`.
- The configured database currently contains 2,534 valid and 93 needs-review timetable entries, 301 subject rows, and 43 classroom rows.
- Active timetable data currently includes FYBA, FYBCom, SYBA, and TYBA.
- Older imports are retained and their timetables can be marked `SUPERSEDED`.

## Existing Strengths To Preserve

- Source uploads and import history are retained.
- Raw cell and raw entry text are retained in reviews and timetable entries.
- Department and division are separate nullable fields.
- Timetable-level context exists and entries reference a timetable.
- Time slots are normalized and referenced by foreign key.
- One cell can generate multiple entries.
- Empty placeholders are filtered by `is_blank_cell`.
- Authentication and frontend API contracts are already integrated.
- Review, confirmation, schedule, availability, classroom, subject, and time-slot APIs exist.
- Unexpected import exceptions are rolled back and recorded as failed imports.

## Problems And Proposed Fixes

### 1. Grid detection is tied to one geometry

- Current behavior: OCR assumes exactly eight vertical boundaries, nine horizontal boundaries, six Monday-Saturday columns, and seven data rows.
- Cause: fixed fractions and image bands in `PdfTimetableParser._detect_grid`, plus fixed loops in `_cells_from_ocr`.
- Evidence: the constants were tuned for the current Modern College BA/BCom scans; FYBSc has not been verified.
- Expected: detect header, day columns, time rows, and table shape from each page, then select a compatible layout template.
- Fix: introduce template detection and a grid result object; retain the existing layout as a named template rather than the universal parser.

### 2. Text-layer PDFs lose layout

- Current behavior: if a PDF has text, `_cells_from_text` flattens it and uses day/time regex fragments.
- Cause: PyMuPDF coordinate blocks/words are not used in the text-layer branch.
- Expected: coordinate extraction should be primary for text PDFs too.
- Fix: extract PyMuPDF words with bounding boxes, then run the same layout/grid/cell pipeline; keep regex text parsing only as a low-confidence fallback.

### 3. Raw extraction is incomplete

- Current behavior: OCR word coordinates exist only in memory. `ParsedCell`, `ImportReview`, and final entries do not store a bounding box, extraction method, OCR flag, OCR confidence, parser/template, or decisions.
- Cause: the base parser contract contains only text and row/column references.
- Expected: raw provenance survives into review/debug data.
- Fix: extend raw cell metadata and review JSON with bounding box, method, template, page confidence, parser version, and decision trace while preserving API compatibility.

### 4. No entry confidence score

- Current behavior: only `VALID`, `NEEDS_REVIEW`, and `INVALID` exist. Tesseract confidence below 20 is discarded, and remaining values are not aggregated.
- Cause: no confidence model in `NormalizedTimetableEntry` or persistence schemas.
- Expected: HIGH/MEDIUM/LOW confidence derived deterministically from layout, context, OCR, room parsing, and validation signals.
- Fix: add confidence level/score to review and timetable entry data and include counts in import summaries.

### 5. Needs-review data enters production

- Current behavior: `ImportService.process_import` calls `_persist_review_record` for both valid and needs-review records.
- Cause: the import service treats review warnings as publishable.
- Evidence: 93 `NEEDS_REVIEW` records currently exist in `timetable_entries`.
- Expected: only validated/high-enough confidence records are published automatically; review records remain staged until accepted.
- Fix: gate production persistence by validation/confidence and preserve explicit confirmation behavior.

### 6. Classroom creation trusts OCR too early

- Current behavior: `TimetableMapper.map_classroom` automatically creates a classroom whenever a room regex matches.
- Cause: mapping and master-data creation are combined.
- Expected: high-confidence room patterns may map/create; ambiguous OCR must remain staged.
- Fix: separate room interpretation from classroom materialization and require sufficient confidence.

### 7. Subject-room parsing is pattern-limited

- Current behavior: trailing 3-4 digit, CC, AB, and limited alphanumeric forms are separated; other room/hall formats remain merged or ambiguous.
- Cause: one `CONFIDENT_ROOM_RE` in `TimetableNormalizer` handles every layout.
- Expected: template-aware room patterns and header-level hall inheritance.
- Fix: use parser/template rules that emit structured subject/room candidates plus an explanation.

### 8. Classroom-only fragments can become subjects

- Current behavior: the validator only requires non-empty subject text. OCR fragments such as standalone room numbers can pass unless another rule happens to flag them.
- Cause: no classroom-only or header-fragment subject validation.
- Expected: obvious room-only values, day headers, times, and placeholders must not become subjects.
- Fix: add deterministic subject sanity rules and low-confidence review outcomes.

### 9. Subject master data can be polluted

- Current behavior: `_get_or_create_subject` runs during immediate persistence; canonicalization is based mainly on matching a department name inside subject text.
- Cause: master-data creation occurs before robust subject classification/review.
- Evidence: the configured database has 301 subject rows after four active class formats, including OCR variants from historical imports.
- Expected: canonical subjects exclude room numbers and category/session labels; uncertain text stays in review.
- Fix: introduce parsed `subject_name`, `subject_code`, and category fields; create/reuse Subject only after validation.

### 10. Subject category and session semantics are collapsed

- Current behavior: only `activity_type` exists, and it recognizes PT and a narrow SEC case. Major, Minor, AEC, VSC, GE, lecture, practical, and delivery mode often remain in `subject_text`.
- Cause: no structured subject/session/delivery fields.
- Expected: preserve `subject_type`, `session_type`, and `delivery_mode` independently.
- Fix: add conservative classifiers and nullable persisted fields; retain raw text.

### 11. Department ownership and timetable context can be confused

- Current behavior: timetable department context is inherited correctly, but subject ownership is inferred by searching known department names and otherwise falls back to the timetable department.
- Cause: `ImportService._resolve_subject_department` mixes cohort/program context with subject ownership.
- Expected: timetable department and subject-owning department remain distinct; unknown ownership stays null.
- Fix: do not default subject ownership when the source does not establish it; allow explicit aliases/catalog matching.

### 12. Division handling is independent but narrow

- Current behavior: department and division are separate, but PDF division extraction accepts only one letter through `_detect_metadata`.
- Expected: retain independent optional fields and support actual multi-character division labels without fabrication.
- Fix: template metadata rules with normalized but source-preserving division values.

### 13. Timetable context is a loose dictionary

- Current behavior: page/document context is passed in untyped metadata dictionaries and copied into cells.
- Cause: there is no explicit context data structure.
- Expected: a typed context with source, class, department, division, semester, year, hall, template, and confidence.
- Fix: add a `TimetableContext` dataclass and deterministic page-to-cell inheritance.

### 14. Multi-entry cell grouping is heuristic

- Current behavior: `_combine_cell_lines` ends an entry when a line ends in selected room/location patterns, then `split_cell_entries` splits only on `/`.
- Cause: line geometry is reduced to strings before interpretation.
- Expected: preserve line bounding boxes and group lines using vertical proximity, room alignment, and template rules.
- Fix: represent raw cell lines/words structurally and let the active template group candidates.

### 15. Header leakage is insufficiently guarded

- Current behavior: `_looks_like_timetable_content` only checks letter counts and a few short tokens.
- Cause: no explicit header region/cell-role classification.
- Evidence: previous imports produced malformed department strings and header fragments before regex tightening.
- Expected: header, day, time, note/footer, and data regions are distinct.
- Fix: have grid/template detection return region roles and reject non-data cells before normalization.

### 16. Time extraction partly guesses fixed hours

- Current behavior: `_times_for_row` falls back to `07:15 + row_index` when OCR does not provide a usable pair.
- Cause: the current template embeds a seven-period schedule assumption.
- Expected: infer times from detected row headers or a selected template and mark fallback-derived times in trace/confidence.
- Fix: move fallback schedules into template configuration and reduce confidence when used.

### 17. OCR correction is not controlled or traceable

- Current behavior: low-confidence words are removed; remaining OCR output is normalized mostly by whitespace and ad hoc regex.
- Cause: no bounded OCR correction layer or trace record.
- Expected: conservative known-token corrections with original text retained and confidence penalties.
- Fix: add normalization decisions to trace JSON; never silently rewrite uncertain semantic text.

### 18. Duplicate identity includes raw OCR text

- Current behavior: the unique timetable-entry constraint includes `raw_entry_text`.
- Cause: source identity and semantic schedule identity are combined.
- Expected: detect semantic duplicates by timetable/day/time/subject/room while retaining multiple source references where legitimate.
- Fix: add duplicate detection before persistence and report possible duplicates instead of relying only on the database constraint.

### 19. A single bad cell can fail the whole import

- Current behavior: one database length/integrity error rolls back the complete processing transaction and marks the import failed.
- Cause: processing has import-level exception handling but no per-cell savepoint/error capture.
- Expected: malformed cells become failed review records while safe pages/cells survive.
- Fix: use nested transactions or isolate parsing from bulk persistence, recording per-cell failures.

### 20. Reprocessing and caching are absent

- Current behavior: identical uploaded bytes are stored and OCR-processed repeatedly.
- Evidence: the uploads directory and import history contain repeated copies of the same FYBA/SYBA/FYBCom documents.
- Expected: content hashing identifies duplicates and permits cached raw extraction or explicit reprocessing.
- Fix: store SHA-256 and parser version; reuse only compatible extraction results.

### 21. Quality reports are incomplete

- Current behavior: `summary_json` records cells, generated/valid/review/invalid counts, rooms, departments/programs, and warnings.
- Missing: pages successfully extracted, confidence distribution, duplicate count, unparsed cells, OCR pages, template, parser version, and normalized preview.
- Fix: introduce a structured extraction-quality report while keeping existing summary keys.

### 22. Debugging is insufficient

- Current behavior: raw text and source references exist, but grid boundaries, boxes, OCR words, parser decisions, and visual overlays are unavailable.
- Expected: opt-in trace mode that explains each interpretation without bloating normal imports.
- Fix: configurable trace JSON and optional page overlay artifacts stored under the import.

### 23. Schema migration practice is fragile

- Current behavior: Alembic is installed, but startup code uses `create_all` plus hand-written `ALTER TABLE` helpers only outside production.
- Expected: versioned migrations with repeatable upgrade paths.
- Fix: add Alembic revisions for new nullable fields and preserve startup compatibility only as a temporary bridge.

### 24. Automated PDF coverage is too small

- Current behavior: tests cover CSV flow and three isolated parser helpers; no real PDF regression assertions exist.
- Expected: fixture/golden tests across available layouts, with sampled visual ground truth.
- Fix: add compact expected manifests and quality assertions for FYBA, FYBCom, SYBA, TYBA, and FYBSc.

### 25. Frontend hides extraction provenance

- Current behavior: timetable management shows validation status and source page but not confidence, parser/template, warnings, or review decisions.
- Expected: uncertain extraction is visible and traceable without breaking the current timetable view.
- Fix: extend responses additively and add review/quality views later; retain current fields.

## Proposed Incremental Architecture

```text
PDF
  -> PDF type/page capability detection
  -> coordinate words (PyMuPDF) OR rendered OCR words (Tesseract)
  -> RawPage / RawWord / bounding boxes
  -> layout template detector
  -> GridResult (header, days, times, cells, geometry)
  -> TimetableContext inheritance
  -> RawTimetableCell
  -> template-aware candidate grouping
  -> ParsedTimetableEntry
  -> controlled normalization + decision trace
  -> validation + confidence scoring + duplicate analysis
  -> ImportReview staging
  -> validated Timetable/Entry/Subject/Classroom persistence
  -> quality report + optional debug overlay
```

The existing parser, normalizer, validator, review API, and persistence service should be evolved into these layers rather than replaced wholesale.

## Implementation Order

1. Extend raw/parser contracts with provenance, typed context, parser/template identity, and decision trace.
2. Add confidence scoring and stricter validation without changing existing response fields.
3. Add named layout templates, retaining the current Modern College grid as the first implementation.
4. Make text-layer extraction coordinate-aware.
5. Separate category/session/delivery fields and harden subject/room interpretation.
6. Stage needs-review records instead of publishing them automatically.
7. Add per-cell fault isolation, duplicate analysis, quality reports, and debug mode.
8. Add safe schema migrations and additive API fields.
9. Build real-PDF golden tests and compare old/new extraction.

## Backward Compatibility Constraints

- Keep current upload, review, timetable, entry, schedule, classroom, subject, and time-slot routes.
- Keep existing response fields; new provenance/confidence fields must be additive.
- Preserve raw text and historical imports.
- Do not invent faculty, department, division, room, semester, or subject ownership.
- Keep CSV/Excel support through the shared parser contract.
- Do not start frontend/backend servers as part of implementation.
