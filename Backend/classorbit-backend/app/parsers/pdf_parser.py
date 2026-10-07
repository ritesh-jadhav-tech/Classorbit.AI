import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from app.core.config import get_settings
from app.parsers.base import ParsedCell, ParsedDocument, ParserCapabilityError
from app.parsers.templates import TimetableLayoutTemplate, detect_template
from app.utils.text_normalization import is_blank_cell, normalize_space
from app.utils.time_utils import DAY_ALIASES, normalize_day, parse_time_value, time_to_string


@dataclass
class OcrWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2


@dataclass
class OcrPage:
    page_number: int
    image: object
    words: list[OcrWord]
    text: str
    extraction_method: str = "OCR"
    ocr_used: bool = True


@dataclass(frozen=True)
class DetectedColumn:
    label: str
    left: int
    right: int


@dataclass(frozen=True)
class DetectedGrid:
    time_left: int
    time_right: int
    columns: tuple[DetectedColumn, ...]
    verticals: tuple[int, ...]
    horizontals: tuple[int, ...]
    header_box: tuple[int, int, int, int]


class PdfTimetableParser:
    supported_extensions = (".pdf",)

    def parse(self, source_path: Path) -> ParsedDocument:
        try:
            import pymupdf
        except ImportError:
            try:
                import fitz as pymupdf
            except ImportError as exc:
                raise RuntimeError(
                    "PDF import requires PyMuPDF. Install requirements in the same Python environment that runs Uvicorn."
                ) from exc

        document = pymupdf.open(source_path)
        warnings: list[str] = []
        page_texts: list[tuple[int, str]] = []
        for page_index in range(document.page_count):
            text = normalize_space(document[page_index].get_text("text"))
            if text:
                page_texts.append((page_index + 1, text))

        document_text = " ".join(text for _, text in page_texts)
        template = detect_template(document_text)
        if page_texts:
            metadata = self._detect_metadata(document_text)
            coordinate_pages = self._coordinate_pages(document)
            cells = self._cells_from_ocr(coordinate_pages, metadata, template)
            if not cells:
                cells = self._cells_from_text(page_texts, metadata)
                warnings.append("Coordinate grid extraction failed; low-confidence text fallback was used.")
        else:
            ocr_pages = self._ocr_pages(document)
            page_texts = [(page.page_number, page.text) for page in ocr_pages]
            metadata = self._detect_metadata(" ".join(text for _, text in page_texts))
            template = detect_template(" ".join(text for _, text in page_texts))
            cells = self._cells_from_ocr(ocr_pages, metadata, template)
            warnings.append("PDF has no usable text layer; grid-aware OCR fallback was used.")

        if not cells:
            warnings.append("No timetable-like cells were detected. Upload will need admin review or OCR tuning.")

        return ParsedDocument(
            source_path=source_path,
            source_type="PDF",
            page_count=document.page_count,
            metadata=metadata,
            cells=cells,
            warnings=warnings,
            parser_name=self.__class__.__name__,
            template_name=template.name,
            pages_extracted=len({cell.source_page for cell in cells if cell.source_page}),
            ocr_pages=[page for page, _ in page_texts] if not document_text else [],
            trace={"strategy": template.name, "page_count": document.page_count, "source_driven_layout": True},
        )

    def _coordinate_pages(self, document) -> list[OcrPage]:
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
        from PIL import Image

        pages: list[OcrPage] = []
        scale = 3
        for page_index in range(document.page_count):
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            words = [
                OcrWord(
                    text=normalize_space(str(item[4])),
                    left=round(item[0] * scale),
                    top=round(item[1] * scale),
                    width=round((item[2] - item[0]) * scale),
                    height=round((item[3] - item[1]) * scale),
                    confidence=100.0,
                )
                for item in page.get_text("words")
                if normalize_space(str(item[4]))
            ]
            if words:
                pages.append(
                    OcrPage(
                        page_number=page_index + 1,
                        image=image,
                        words=words,
                        text=normalize_space(" ".join(word.text for word in words)),
                        extraction_method="PDF_COORDINATES",
                        ocr_used=False,
                    )
                )
        return pages

    def _ocr_pages(self, document) -> list[OcrPage]:
        try:
            from PIL import Image
        except ImportError as exc:
            raise ParserCapabilityError(
                "This PDF appears to be scanned and image rendering requires Pillow."
            ) from exc

        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf

        pages: list[OcrPage] = []
        for page_index in range(document.page_count):
            pixmap = document[page_index].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            page = self._ocr_image_page(image, page_index + 1)
            if page:
                pages.append(page)

        if not pages:
            raise ParserCapabilityError("OCR completed but did not return readable timetable text.")
        return pages

    def _ocr_image_page(self, image, page_number: int) -> OcrPage | None:
        try:
            import pytesseract
        except ImportError as exc:
            raise ParserCapabilityError("OCR requires pytesseract and the Tesseract executable.") from exc

        tesseract_cmd = self._find_tesseract()
        if tesseract_cmd is None:
            raise ParserCapabilityError(
                "OCR could not find Tesseract. Install Tesseract or set TESSERACT_CMD to tesseract.exe."
            )
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        try:
            data = pytesseract.image_to_data(image, config="--psm 11", output_type=pytesseract.Output.DICT)
        except Exception as exc:
            raise ParserCapabilityError(
                "OCR could not run. Check TESSERACT_CMD and the Tesseract installation."
            ) from exc

        words: list[OcrWord] = []
        for index, raw_text in enumerate(data["text"]):
            text = normalize_space(raw_text)
            if not text:
                continue
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1
            if confidence < 20:
                continue
            words.append(
                OcrWord(
                    text=text,
                    left=int(data["left"][index]),
                    top=int(data["top"][index]),
                    width=int(data["width"][index]),
                    height=int(data["height"][index]),
                    confidence=confidence,
                )
            )
        if not words:
            return None
        return OcrPage(
            page_number=page_number,
            image=image,
            words=words,
            text=normalize_space(" ".join(word.text for word in words)),
        )

    def _cells_from_ocr(
        self,
        pages: list[OcrPage],
        document_metadata: dict[str, str | None],
        template: TimetableLayoutTemplate | None = None,
    ) -> list[ParsedCell]:
        template = template or detect_template()
        cells: list[ParsedCell] = []
        known_slots: list[tuple[str, str]] = []
        for page in pages:
            detected_page_metadata = self._detect_metadata(page.text)
            detected_page_metadata.update(self._positioned_header_metadata(page.words))
            page_metadata = {
                **document_metadata,
                **{
                    key: value
                    for key, value in detected_page_metadata.items()
                    if value is not None and value != {}
                },
            }
            page_metadata["attributes"] = {
                **(document_metadata.get("attributes") or {}),
                **(detected_page_metadata.get("attributes") or {}),
            }
            page_metadata["template_name"] = template.name
            grid = self._detect_grid(page.image, page.words, template)
            if grid is None:
                continue
            time_rows = self._time_rows_from_words(page.words, grid.time_left, grid.time_right)
            if time_rows:
                candidate_slots = [(start, end) for _, _, start, end in time_rows]
                if len(candidate_slots) > len(known_slots):
                    known_slots = candidate_slots
            elif known_slots:
                time_rows = self._time_rows_from_known_slots(
                    page.words, grid.time_left, grid.time_right, known_slots
                )
            page_metadata["column_order"] = [column.label for column in grid.columns]
            page_metadata["time_slot_order"] = [f"{start}-{end}" for _, _, start, end in time_rows]
            page_metadata["layout"] = {
                "header_box": list(grid.header_box),
                "verticals": list(grid.verticals),
                "horizontals": list(grid.horizontals),
            }

            for row_index, (top, bottom, start_time, end_time) in enumerate(time_rows):
                time_text = self._words_in_box(page.words, grid.time_left, top, grid.time_right, bottom)

                for column_index, column in enumerate(grid.columns):
                    day = column.label
                    left = column.left
                    right = column.right
                    source_raw_text = self._words_in_box(page.words, left, top, right, bottom)
                    raw_text = self._normalize_short_activity_ocr(source_raw_text)
                    if is_blank_cell(raw_text) or not self._looks_like_timetable_content(raw_text):
                        continue
                    selected_words = self._selected_words(page.words, left, top, right, bottom)
                    confidence = (
                        sum(word.confidence for word in selected_words) / len(selected_words) if selected_words else None
                    )
                    cells.append(
                        ParsedCell(
                            raw_cell_text=raw_text,
                            class_name=page_metadata.get("class_name"),
                            division=page_metadata.get("division"),
                            day=day,
                            start_time_text=start_time,
                            end_time_text=end_time,
                            source_page=page.page_number,
                            source_row=row_index + 1,
                            source_column=day,
                            source_cell_reference=f"page:{page.page_number}:row:{row_index + 1}:day:{day}",
                            bounding_box=(left, top, right, bottom),
                            extraction_method=page.extraction_method,
                            ocr_used=page.ocr_used,
                            ocr_confidence=confidence,
                            parser_name=self.__class__.__name__,
                            template_name=template.name,
                            trace=[
                                {
                                    "decision": "detected_grid_cell",
                                    "column": day,
                                    "column_index": column_index,
                                    "row": row_index + 1,
                                },
                                {"decision": "time_row", "raw": time_text, "start": start_time, "end": end_time},
                            ] + ([{
                                "decision": "ocr_short_activity_correction",
                                "raw": source_raw_text,
                                "normalized": raw_text,
                            }] if raw_text != source_raw_text else []),
                            metadata={
                                **page_metadata,
                                "raw_lines": self._line_texts_in_box(page.words, left, top, right, bottom),
                            },
                        )
                    )
        return cells

    @staticmethod
    def _positioned_header_metadata(words: list[OcrWord]) -> dict[str, str]:
        labels = {
            "class": "class_name",
            "div": "division",
            "division": "division",
            "section": "division",
        }
        values: dict[str, str] = {}
        ordered = sorted(words, key=lambda word: (word.center_y, word.left))
        for label_word in ordered:
            label = re.sub(r"[^a-z]", "", label_word.text.lower())
            target = labels.get(label)
            if not target:
                continue
            line_words = sorted(
                (
                    word for word in words
                    if word.left >= label_word.left + label_word.width
                    and abs(word.center_y - label_word.center_y) <= 15
                ),
                key=lambda word: word.left,
            )
            selected: list[OcrWord] = []
            previous_right = label_word.left + label_word.width
            for word in line_words:
                if word.left - previous_right > 70:
                    break
                if re.sub(r"[^a-z]", "", word.text.lower()) in labels:
                    break
                selected.append(word)
                previous_right = word.left + word.width
            value = normalize_space(" ".join(word.text for word in selected)).strip("-:|")
            if value:
                values[target] = value
        return values

    def _time_rows_from_words(
        self, words: list[OcrWord], left: int, right: int
    ) -> list[tuple[int, int, str, str]]:
        time_words = [
            word
            for word in words
            if left + 3 < word.center_x < right - 3
            and re.search(r"\b\d{1,2}[.:]\d{2}\b", word.text, re.I)
        ]
        time_words.sort(key=lambda word: word.center_y)
        if len(time_words) < 2:
            return []
        if len(time_words) % 2:
            time_words = time_words[:-1]

        pairs = [(time_words[index], time_words[index + 1]) for index in range(0, len(time_words), 2)]
        day_names = set(DAY_ALIASES)
        header_bottom = max(
            (
                word.top + word.height
                for word in words
                if word.text.strip().lower().rstrip(".") in day_names
                and word.center_y < pairs[0][0].center_y
            ),
            default=0,
        )
        rows: list[tuple[int, int, str, str]] = []
        for index, (start_word, end_word) in enumerate(pairs):
            if index == 0:
                top = round(start_word.center_y - max(25, (end_word.center_y - start_word.center_y) * 0.6))
                top = max(top, header_bottom + 4)
            else:
                top = round((pairs[index - 1][1].center_y + start_word.center_y) / 2)
            if index + 1 < len(pairs):
                bottom = round((end_word.center_y + pairs[index + 1][0].center_y) / 2)
            else:
                bottom = round(end_word.center_y + max(25, (end_word.center_y - start_word.center_y) * 0.6))
            start_time = time_to_string(parse_time_value(start_word.text))
            end_time = time_to_string(parse_time_value(end_word.text))
            if bottom > top and start_time and end_time and start_time != end_time:
                rows.append((top, bottom, start_time, end_time))
        return rows

    def _time_rows_from_known_slots(
        self,
        words: list[OcrWord],
        left: int,
        right: int,
        slots: list[tuple[str, str]],
    ) -> list[tuple[int, int, str, str]]:
        tokens = [
            (word, time_to_string(parse_time_value(word.text)))
            for word in words
            if left + 3 < word.center_x < right - 3
            and re.search(r"\b\d{1,2}[.:]\d{2}\b", word.text, re.I)
        ]
        tokens = [(word, value) for word, value in tokens if value]
        tokens.sort(key=lambda item: item[0].center_y)
        if not tokens:
            return []

        deltas = [
            right_word.center_y - left_word.center_y
            for (left_word, left_value), (right_word, right_value) in zip(tokens, tokens[1:])
            if left_value != right_value and 15 < right_word.center_y - left_word.center_y < 100
        ]
        internal_gap = median(deltas) if deltas else 45
        cursor = 0
        centers: list[tuple[float, float, str, str]] = []
        for start_time, end_time in slots:
            start_word = next(
                (word for word, value in tokens[cursor:] if value == start_time),
                None,
            )
            start_index = next(
                (index for index in range(cursor, len(tokens)) if tokens[index][1] == start_time),
                None,
            )
            search_from = start_index + 1 if start_index is not None else cursor
            end_index = next(
                (index for index in range(search_from, len(tokens)) if tokens[index][1] == end_time),
                None,
            )
            end_word = tokens[end_index][0] if end_index is not None else None
            if not start_word and not end_word:
                continue
            start_center = start_word.center_y if start_word else end_word.center_y - internal_gap
            end_center = end_word.center_y if end_word else start_center + internal_gap
            centers.append((start_center, end_center, start_time, end_time))
            if end_index is not None:
                cursor = end_index + 1

        rows: list[tuple[int, int, str, str]] = []
        for index, (start_center, end_center, start_time, end_time) in enumerate(centers):
            top = round(
                (centers[index - 1][1] + start_center) / 2
                if index
                else start_center - max(25, internal_gap * 0.6)
            )
            bottom = round(
                (end_center + centers[index + 1][0]) / 2
                if index + 1 < len(centers)
                else end_center + max(25, internal_gap * 0.6)
            )
            if bottom > top:
                rows.append((top, bottom, start_time, end_time))
        return rows

    def _detect_grid(
        self,
        image,
        words: list[OcrWord],
        template: TimetableLayoutTemplate | None = None,
    ) -> DetectedGrid | None:
        try:
            import numpy as np
        except ImportError as exc:
            raise ParserCapabilityError("Grid-aware PDF OCR requires numpy.") from exc

        gray = np.asarray(image.convert("L"))
        height, width = gray.shape
        dark = gray < 245

        template = template or detect_template()
        header_words = self._detected_column_headers(words, template)
        if len(header_words) < template.minimum_day_columns:
            return None

        header_words.sort(key=lambda item: item[0].center_x)
        header_y = int(median([word.center_y for word, _ in header_words]))
        time_header = min(
            (
                word
                for word in words
                if word.text.strip().lower().rstrip(".:") in {"time", "period", "slot"}
                and word.center_x < header_words[0][0].center_x
                and abs(word.center_y - header_y) <= template.header_y_tolerance * 2
            ),
            key=lambda word: abs(word.center_y - header_y),
            default=None,
        )
        time_words = [
            word
            for word in words
            if word.center_x < header_words[0][0].center_x
            and re.search(r"\b\d{1,2}[.:]\d{2}\b", word.text)
        ]
        if time_header:
            time_center = time_header.center_x
        elif time_words:
            time_center = median([word.center_x for word in time_words])
        else:
            first_gap = header_words[1][0].center_x - header_words[0][0].center_x
            time_center = header_words[0][0].center_x - first_gap

        centers = [float(time_center), *[word.center_x for word, _ in header_words]]
        targets = [round(centers[0] - (centers[1] - centers[0]) / 2)]
        targets.extend(round((left + right) / 2) for left, right in zip(centers, centers[1:]))
        targets.append(round(centers[-1] + (centers[-1] - centers[-2]) / 2))

        last_content_y = max((word.center_y for word in time_words), default=header_y + height * 0.35)
        band_top = max(0, round(header_y - height * 0.02))
        band_bottom = min(height, round(last_content_y + height * 0.04))
        vertical_score = dark[band_top:band_bottom, :].sum(axis=0)
        verticals: list[int] = []
        for index, target in enumerate(targets):
            before = centers[max(0, min(index - 1, len(centers) - 2))]
            after = centers[min(len(centers) - 1, max(index, 1))]
            radius = max(12, round(abs(after - before) * template.boundary_snap_ratio))
            verticals.append(
                self._strongest(vertical_score, max(0, target - radius), min(width, target + radius + 1))
            )
        if any(right <= left for left, right in zip(verticals, verticals[1:])):
            verticals = targets

        columns = tuple(
            DetectedColumn(label=label, left=verticals[index + 1], right=verticals[index + 2])
            for index, (_, label) in enumerate(header_words)
        )
        horizontal_score = dark[:, max(0, verticals[0]) : min(width, verticals[-1] + 1)].sum(axis=1)
        threshold = max((verticals[-1] - verticals[0]) * 0.18, float(np.quantile(horizontal_score, 0.975)))
        horizontals = self._cluster_positions(np.where(horizontal_score >= threshold)[0])
        header_top = min(word.top for word, _ in header_words)
        header_bottom = max(word.top + word.height for word, _ in header_words)
        return DetectedGrid(
            time_left=verticals[0],
            time_right=verticals[1],
            columns=columns,
            verticals=tuple(verticals),
            horizontals=tuple(horizontals),
            header_box=(verticals[0], header_top, verticals[-1], header_bottom),
        )

    @staticmethod
    def _detected_column_headers(
        words: list[OcrWord], template: TimetableLayoutTemplate
    ) -> list[tuple[OcrWord, str]]:
        candidates = [(word, normalize_day(word.text)) for word in words]
        candidates = [(word, label) for word, label in candidates if label]
        if not candidates:
            return []
        groups: list[list[tuple[OcrWord, str]]] = []
        for candidate in sorted(candidates, key=lambda item: item[0].center_y):
            group_center = median([item[0].center_y for item in groups[-1]]) if groups else None
            if group_center is None or abs(candidate[0].center_y - group_center) > template.header_y_tolerance:
                groups.append([candidate])
            else:
                groups[-1].append(candidate)
        selected = max(groups, key=lambda group: len({label for _, label in group}))
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_label = {label: word for word, label in selected}
        indexes = sorted(weekday_order.index(label) for label in by_label if label in weekday_order)
        if len(indexes) >= 2:
            first_index, last_index = indexes[0], indexes[-1]
            first_word = by_label[weekday_order[first_index]]
            last_word = by_label[weekday_order[last_index]]
            step = (last_word.center_x - first_word.center_x) / (last_index - first_index)
            for index in range(first_index, last_index + 1):
                label = weekday_order[index]
                if label in by_label:
                    continue
                center_x = first_word.center_x + step * (index - first_index)
                by_label[label] = OcrWord(
                    text=label,
                    left=round(center_x - first_word.width / 2),
                    top=first_word.top,
                    width=first_word.width,
                    height=first_word.height,
                    confidence=min(first_word.confidence, last_word.confidence) * 0.8,
                )
            selected = [(by_label[weekday_order[index]], weekday_order[index]) for index in range(first_index, last_index + 1)]
        header_y = median([word.center_y for word, _ in selected])
        selected_centers = sorted(word.center_x for word, _ in selected)
        typical_step = median(
            right - left for left, right in zip(selected_centers, selected_centers[1:])
        ) if len(selected_centers) > 1 else 0
        extra_start_x = selected_centers[-1] + typical_step * 0.45
        known_word_ids = {id(word) for word, _ in selected}
        extra_words = [
            word
            for word in words
            if id(word) not in known_word_ids
            and abs(word.center_y - header_y) <= max(12, template.header_y_tolerance / 2)
            and word.center_x > extra_start_x
            and word.text.strip().lower().rstrip(".:") not in {"time", "period", "slot"}
            and re.fullmatch(r"[A-Za-z][A-Za-z&/-]*", word.text.strip())
        ]
        extra_groups: list[list[OcrWord]] = []
        for word in sorted(extra_words, key=lambda item: item.left):
            if not extra_groups or word.left - (extra_groups[-1][-1].left + extra_groups[-1][-1].width) > 24:
                extra_groups.append([word])
            else:
                extra_groups[-1].append(word)
        for group in extra_groups:
            label = normalize_space(" ".join(word.text for word in group))
            if not label or normalize_day(label):
                continue
            left = min(word.left for word in group)
            right = max(word.left + word.width for word in group)
            selected.append(
                (
                    OcrWord(
                        text=label,
                        left=left,
                        top=min(word.top for word in group),
                        width=right - left,
                        height=max(word.height for word in group),
                        confidence=sum(word.confidence for word in group) / len(group),
                    ),
                    label,
                )
            )
        return selected

    @staticmethod
    def _cluster_positions(values) -> list[int]:
        groups: list[list[int]] = []
        for raw_value in values:
            value = int(raw_value)
            if not groups or value - groups[-1][-1] > 4:
                groups.append([value])
            else:
                groups[-1].append(value)
        return [round(sum(group) / len(group)) for group in groups]

    @staticmethod
    def _strongest(score, start: int, end: int) -> int:
        import numpy as np

        if end <= start:
            return start
        return int(start + np.argmax(score[start:end]))

    @classmethod
    def _words_in_box(cls, words: list[OcrWord], left: int, top: int, right: int, bottom: int) -> str:
        return cls._combine_cell_lines(cls._line_texts_in_box(words, left, top, right, bottom)).strip("|_")

    @classmethod
    def _line_texts_in_box(
        cls, words: list[OcrWord], left: int, top: int, right: int, bottom: int
    ) -> list[str]:
        selected = cls._selected_words(words, left, top, right, bottom)
        selected.sort(key=lambda word: (word.center_y, word.left))

        lines: list[list[OcrWord]] = []
        for word in selected:
            if not lines or abs(word.center_y - sum(item.center_y for item in lines[-1]) / len(lines[-1])) > 12:
                lines.append([word])
            else:
                lines[-1].append(word)
        return [" ".join(item.text for item in sorted(line, key=lambda item: item.left)) for line in lines]

    @staticmethod
    def _selected_words(words: list[OcrWord], left: int, top: int, right: int, bottom: int) -> list[OcrWord]:
        return [
            word
            for word in words
            if left + 3 < word.center_x < right - 3 and top + 2 < word.center_y < bottom - 2
        ]

    @staticmethod
    def _combine_cell_lines(line_texts: list[str]) -> str:
        lines = [normalize_space(line).strip("|_") for line in line_texts if normalize_space(line)]
        if not lines or any("/" in line for line in lines):
            return normalize_space(" ".join(lines))

        entries: list[str] = []
        pending: list[str] = []
        room_at_end = re.compile(r"(?:\b\d{3,4}[A-Z]?|\b(?:CC|AB)\s*[- ]?\s*\d{1,2})$", re.I)
        location_at_end = re.compile(r"\([^)]*(?:department|online|lab)[^)]*\)$", re.I)
        headings = re.compile(r"^(?:minor|major|vsc|sec|aec|oe|sem(?:ester)?\s*[ivx]+)$", re.I)

        for line in lines:
            if headings.fullmatch(line) and not pending:
                continue
            pending.append(line)
            candidate = normalize_space(" ".join(pending))
            if room_at_end.search(candidate) or location_at_end.search(candidate) or candidate.lower().endswith("(online)"):
                entries.append(candidate)
                pending = []
        if pending:
            entries.append(normalize_space(" ".join(pending)))
        return " / ".join(entries)

    @staticmethod
    def _looks_like_timetable_content(value: str) -> bool:
        text = normalize_space(value).strip("|_=~-")
        letters = re.sub(r"[^A-Za-z]", "", text).upper()
        if len(letters) < 2:
            return False
        if len(text) <= 4 and letters not in {"PT", "OE", "SEC"}:
            return False
        return True

    @staticmethod
    def _normalize_short_activity_ocr(value: str) -> str:
        compact = re.sub(r"[^A-Z0-9]", "", normalize_space(value).upper())
        # Tesseract commonly confuses the isolated printed label "P.T." with PG, PI, PL, or P1.
        if compact in {"PT", "PG", "PI", "PL", "P1"}:
            return "P.T."
        return value

    @staticmethod
    def _find_tesseract() -> str | None:
        configured = get_settings().tesseract_cmd
        if configured:
            configured_path = Path(configured).expanduser()
            if configured_path.is_file():
                return str(configured_path)
        discovered = shutil.which("tesseract")
        if discovered:
            return discovered
        candidates = (
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        )
        return next((str(path) for path in candidates if path.is_file()), None)

    def _detect_metadata(self, text: str) -> dict[str, Any]:
        academic_year = None
        year_match = re.search(r"(20\d{2})\s*[-–]\s*(20\d{2})", text)
        if year_match:
            academic_year = f"{year_match.group(1)}-{year_match.group(2)}"

        class_name = None
        class_match = re.search(
            r"\b(?:Class|Programme\s+Class|Course\s+Class)\.?\s*[:\-]\s*"
            r"(.{1,80}?)(?=\s+(?:Div(?:ision)?|Section|Department|Dept|Hall|Room|Semester|Sem|Batch|Group)\.?\s*(?:[:\-]\s*)?|\s+(?:Time(?:\s*Table)?|Timetable|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b|$)",
            text,
            re.I,
        )
        if class_match:
            class_name = normalize_space(class_match.group(1)).strip("-:|")

        division = None
        division_match = re.search(
            r"\b(?:Div(?:ision)?|Section)\.?\s*(?:[:\-]\s*)?"
            r"(.+?)(?=\s+(?:Class|Department|Dept|Hall|Room|Semester|Sem|Batch|Group)\.?\s*(?:[:\-]\s*)?|\s+(?:Time\s*Table|Timetable)|$)",
            text,
            re.I,
        )
        if division_match:
            division = normalize_space(division_match.group(1)).strip("-:|")

        hall_name = None
        hall_match = re.search(
            r"\b(?:Hall(?:\s*(?:No|Number))?|Classroom|Room(?:\s*(?:No|Number))?)\.?\s*[:\-]\s*"
            r"(.+?)(?=\s+(?:Class|Div(?:ision)?|Section|Department|Semester|Sem|Batch|Group)\.?\s*(?:[:\-]\s*)?|\s+(?:Time(?:\s*Table)?|Timetable|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b|$)",
            text,
            re.I,
        )
        if hall_match:
            hall_name = normalize_space(hall_match.group(1))

        college_name = None
        college_match = re.search(r"((?:Modern|[A-Z][A-Za-z]+).{0,160}?College.{0,160}?)(?:Time\s*Table|Timetable)", text, re.I)
        if college_match:
            college_name = normalize_space(college_match.group(1))

        department_name = None
        program_name = None
        department_match = re.search(
            r"Department\s*[:\-]\s*(.+?)(?=\s+(?:(?:[^A-Za-z0-9\s]{1,4}\s*)?Time\b|Revised|Timetable|Class\s*[:\-]|Academic\s+Year)|$)",
            text,
            re.I,
        )
        if department_match:
            program_name = normalize_space(department_match.group(1)).strip("-:|")
            variant_match = re.match(r"^(.+?\((?:Non[- ]?Grant|Grant)\))", program_name, re.I)
            if variant_match:
                program_name = normalize_space(variant_match.group(1))
            department_name = normalize_space(
                re.sub(r"\s*\((?:Non[- ]?Grant|Grant)\)\s*$", "", program_name, flags=re.I)
            )

        semester = self._labeled_value(text, ("semester", "sem"))
        attributes: dict[str, str] = {}
        for key, labels in {
            "batch": ("batch",),
            "group": ("group", "practical group"),
            "faculty": ("faculty", "teacher", "instructor"),
            "course": ("course", "program", "programme"),
        }.items():
            value = self._labeled_value(text, labels)
            if value:
                attributes[key] = value
        known_labels = {
            "class", "course class", "programme class", "division", "div", "section", "department",
            "dept", "hall", "hall no", "hall number", "classroom", "room", "room no", "room number",
            "semester", "sem", "batch", "group", "practical group", "faculty", "teacher", "instructor",
            "course", "program", "programme",
        }
        for match in re.finditer(r"\b([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,2})\s*:\s*([^:]{1,120})", text):
            label = normalize_space(match.group(1)).lower().rstrip(".")
            if label in known_labels:
                continue
            value = normalize_space(match.group(2))
            value = re.split(r"\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Time)\b", value, 1, flags=re.I)[0]
            if value:
                attributes[f"source_{label.replace(' ', '_')}"] = value

        return {
            "college_name": college_name,
            "academic_year": academic_year,
            "class_name": class_name,
            "division": division,
            "hall_name": hall_name,
            "room_hint": hall_name,
            "department_name": department_name,
            "program_name": program_name,
            "semester": semester,
            "attributes": attributes,
        }

    @staticmethod
    def _labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
        label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
        next_label = r"Class|Div(?:ision)?|Section|Department|Dept|Hall|Room|Semester|Sem|Batch|Group|Faculty|Teacher|Instructor|Course|Program(?:me)?"
        match = re.search(
            rf"\b(?:{label_pattern})\.?\s*[:\-]\s*(.+?)"
            rf"(?=\s+(?:{next_label})\.?\s*[:\-]|\s+(?:Time\s*Table|Timetable)|$)",
            text,
            re.I,
        )
        return normalize_space(match.group(1)).strip("-:|") if match else None

    def _cells_from_text(self, page_texts: list[tuple[int, str]], metadata: dict[str, str | None]) -> list[ParsedCell]:
        day_names = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun"
        time_pattern = r"\d{1,2}[.:]\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?"
        row_re = re.compile(
            rf"\b(?P<day>{day_names})\b.*?(?P<time>{time_pattern}\s*(?:-|to|–)\s*{time_pattern})\s+(?P<entry>.+)",
            re.I,
        )
        cells: list[ParsedCell] = []
        for page_number, text in page_texts:
            fragments = re.split(
                r"(?=\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b)",
                text,
            )
            for row_index, fragment in enumerate(fragments, start=1):
                match = row_re.search(fragment)
                if not match:
                    continue
                cells.append(
                    ParsedCell(
                        raw_cell_text=normalize_space(match.group("entry")),
                        class_name=metadata.get("class_name"),
                        division=metadata.get("division"),
                        day=match.group("day"),
                        time_text=match.group("time"),
                        source_page=page_number,
                        source_row=row_index,
                        source_column="text",
                        source_cell_reference=f"page:{page_number}:fragment:{row_index}",
                        metadata=dict(metadata),
                    )
                )
        return cells
