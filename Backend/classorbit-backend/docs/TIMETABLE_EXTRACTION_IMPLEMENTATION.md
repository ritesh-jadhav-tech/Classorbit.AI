# Timetable Extraction Upgrade Report

Date: 2026-09-21

## A. Existing System Analysis

The original flow was `upload -> parser factory -> PDF text/OCR parser -> normalizer -> validator -> mapper -> import review/timetable tables`. PyMuPDF handled readable text and rendered scanned pages; Tesseract supplied OCR. The PDF path flattened text or used fixed grid geometry, then regular expressions interpreted each result. `ImportService` normalized records, created master data, and persisted accepted timetable entries.

The detailed pre-change architecture, ownership map, database flow, and evidence are documented in [TIMETABLE_EXTRACTION_AUDIT.md](TIMETABLE_EXTRACTION_AUDIT.md). That audit was completed before implementation changes.

## B. Problems Discovered

The audit found 25 code-supported issues. The highest-impact issues were fixed geometry across different layouts, loss of word coordinates and OCR confidence, room numbers entering subject text, header/time fragments entering cells, no parser/template provenance, no confidence score, no semantic duplicate check, uncertain records entering production, import-wide failure from one record, and no reproducible quality report.

The old system also collapsed subject categories into names, could not inherit page-level halls, guessed row times from row indexes, and did not explain why a token became a room. Department and division were already separate in parts of the model, but that distinction was not consistently carried through extraction and persistence.

## C. Changes Implemented

- `app/parsers/base.py`: expanded the raw contract with typed context, bounding boxes, extraction method, OCR state/confidence, parser/template identity, and decision trace.
- `app/parsers/pdf_parser.py`: added coordinate-word extraction, OCR fallback with word confidence, grid-cell extraction, printed-time row detection, context/header inheritance, hall detection, and raw cell provenance.
- `app/parsers/templates.py`: introduced independently selectable FYBA, FYBCom, FYBSc, and department-layout templates while sharing one extraction engine.
- `app/parsers/csv_parser.py`, `excel_parser.py`: added provenance and named-column traces for structured imports.
- `app/services/timetable_normalizer.py`: retained raw values while separating subject/room and structuring subject type, session type, delivery mode, department-only Major cells, and inherited halls.
- `app/services/timetable_validator.py`: rejects placeholders, headers, standalone times, and classroom-only fragments; checks required schedule semantics and subject/room separation.
- `app/services/timetable_confidence.py`: assigns deterministic HIGH/MEDIUM/LOW confidence from context, template, OCR quality, warnings, and validation.
- `app/services/timetable_mapper.py`: uncertain records can match existing rooms but cannot create new classroom master data.
- `app/services/import_service.py`: stages uncertain records, persists only validated records, detects semantic duplicates, isolates per-record failures, emits quality summaries, and reuses a completed import for the same SHA-256/parser version.
- `app/services/extraction_quality.py` and `scripts/run_extraction_quality.py`: generate database-free JSON quality reports and normalized previews.
- `app/api/imports.py`: added authenticated quality-report and trace endpoints.
- Models/schemas: added structured type fields, confidence, parser/template/method, bounding boxes, traces, source hash, and parser version without removing existing response fields.
- `app/db/schema_upgrade.py` and `alembic/versions/20260921_01_extraction_provenance.py`: provide idempotent compatibility upgrades and a migration.
- `tests`: added hall inheritance, template selection, noon rollover, category/room separation, confidence, classroom-only rejection, and department-subject inheritance coverage.

## D. New Extraction Architecture

```text
PDF type detection
  -> coordinate words when available
  -> rendered-page OCR fallback when required
  -> template selection
  -> table boundaries, day columns, and printed-time rows
  -> header/context extraction
  -> raw timetable cells with page/row/column/bounding box
  -> zero/one/many interpreted entries per cell
  -> conservative normalization
  -> validation
  -> confidence and duplicate checks
  -> validated production records or review staging
```

The raw source is never replaced by normalized text. Every review record can expose source coordinates, parser/template, raw cell and entry text, interpretation, confidence, warnings, and decisions through `/api/imports/{id}/trace`.

## E. Database Changes

`file_imports` now stores `sha256` and `parser_version`. `import_reviews` and `timetable_entries` now store `subject_code`, `subject_type`, `session_type`, `delivery_mode`, confidence level/score, parser/template/method, and bounding-box JSON. Production entries additionally store trace JSON.

Existing normalized `Department`, `Subject`, `Classroom`, `Timetable`, `TimeSlot`, and `TimetableEntry` relationships remain in use. No duplicate replacement entities were introduced. Existing API fields remain compatible; new fields and endpoints are additive.

## F. Accuracy Improvements

- Day and time come from cell column and printed row structure, not text ordering.
- FYBA, FYBCom, FYBSc, and department timetables use their actual column geometry.
- `11:15-12:15` remains noon and `12:15-1:15` normalizes to `12:15-13:15`.
- Subject/room pairs such as `Hindi CC 4` become subject `Hindi` and room `CC 4`.
- `Hall No. 305` is inherited by each eligible cell while Online/Department locations do not become physical-room mappings.
- TYBA `Major 103` inherits the page department as its subject and retains `MAJOR` as `subject_type`.
- Multiple slash/line-separated subject-room pairs become separate entries.
- Blank cells, dashes, headers, room-only values, and standalone times are invalid rather than subjects.
- OCR confidence and ambiguity lower trust; uncertain data is staged and cannot create classroom or subject production data automatically.

The previous implementation had no reproducible per-PDF quality baseline, so a numeric old/new accuracy percentage would be misleading. Visual comparison confirmed the prior merged/clipped examples; the new report now provides a repeatable baseline for future regression comparisons.

## G. Real-PDF Test Results

All available PDFs were visually inspected and processed. `unparsed cells` was zero for every file. “Review” records are staged rather than inserted into production.

| PDF | Pages | Cells | Entries | Valid | Review | Low/Invalid | Duplicates | Template |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| F.Y.B.A. | 4/4 | 117 | 204 | 200 | 0 | 4 | 0 | FYBA |
| F.Y.B.Com | 4/4 | 89 | 93 | 85 | 8 | 0 | 0 | FYBCom |
| F.Y.BSc | 2/2 | 22 | 22 | 22 | 0 | 0 | 0 | FYBSc |
| S.Y.B.A. | 18/18 | 520 | 934 | 868 | 30 | 36 | 34 | Department |
| T.Y.B.A. | 18/18 | 353 | 673 | 624 | 6 | 43 | 60 | Department |

Confidence totals are recorded in [extraction-quality-2026-09-21.json](extraction-quality-2026-09-21.json), including warnings and human-readable previews. OCR fallback was used for all tested files. The backend regression suite passes: `16 passed`.

No separate FYBSc Microbiology PDF was available. Microbiology cells present in the FYBSc PDF were verified, but the unavailable layout is not claimed as tested.

## H. Remaining Limitations

- Tesseract can still produce spelling errors such as `!` for `I` or omit an initial letter. The system preserves and exposes these rather than applying unsafe dictionary guesses.
- The template registry supports the supplied layouts; substantially different future layouts need a new geometry/template rule.
- Duplicate counts for department files include visually repeated entries that require domain review; they are flagged, not silently deleted.
- Semester is retained when explicitly available but is not invented from subject wording.
- Confidence is deterministic and useful for routing, not a statistical guarantee of correctness.
- Debug data is textual/coordinate based. A rendered image overlay can be added later without changing the extraction contract.
