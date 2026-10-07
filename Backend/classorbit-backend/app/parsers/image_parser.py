from pathlib import Path

from app.parsers.base import ParsedDocument
from app.parsers.pdf_parser import PdfTimetableParser
from app.parsers.templates import detect_template


class ImageTimetableParser:
    supported_extensions = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")

    def parse(self, source_path: Path) -> ParsedDocument:
        try:
            from PIL import Image, ImageSequence
        except ImportError as exc:
            raise RuntimeError("Image import requires Pillow.") from exc

        parser = PdfTimetableParser()
        pages = []
        with Image.open(source_path) as source:
            for page_number, frame in enumerate(ImageSequence.Iterator(source), start=1):
                image = frame.convert("RGB")
                if image.width < 1800:
                    scale = 1800 / image.width
                    image = image.resize((1800, round(image.height * scale)), Image.Resampling.LANCZOS)
                page = parser._ocr_image_page(image, page_number)
                if page:
                    pages.append(page)
        if not pages:
            return ParsedDocument(source_path=source_path, source_type="IMAGE", warnings=["No readable image text was detected."])

        document_text = " ".join(page.text for page in pages)
        metadata = parser._detect_metadata(document_text)
        template = detect_template(document_text)
        cells = parser._cells_from_ocr(pages, metadata, template)
        return ParsedDocument(
            source_path=source_path,
            source_type="IMAGE",
            page_count=len(pages),
            metadata=metadata,
            cells=cells,
            warnings=[] if cells else ["No timetable grid was detected in the image."],
            parser_name=self.__class__.__name__,
            template_name=template.name,
            pages_extracted=len({cell.source_page for cell in cells if cell.source_page}),
            ocr_pages=[page.page_number for page in pages],
            trace={"strategy": template.name, "source_driven_layout": True, "input": "IMAGE"},
        )

