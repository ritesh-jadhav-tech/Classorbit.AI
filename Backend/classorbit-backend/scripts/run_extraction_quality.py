import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parsers.factory import get_parser_for_file
from app.services.extraction_quality import ExtractionQualityAnalyzer


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic timetable extraction quality reports.")
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    analyzer = ExtractionQualityAnalyzer()
    reports = []
    for path in args.pdfs:
        document = get_parser_for_file(path).parse(path)
        report = analyzer.analyze(document)
        reports.append(report)
        print(
            f"{path.name}: {report['timetable_entries_generated']} entries, "
            f"{report['valid']} valid, {report['needs_review']} review, "
            f"{report['validation_failures']} invalid",
            flush=True,
        )

    payload = json.dumps(reports, indent=2, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
