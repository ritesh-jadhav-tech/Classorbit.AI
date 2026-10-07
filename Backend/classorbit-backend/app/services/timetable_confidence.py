from app.models.enums import ConfidenceLevel, ValidationStatus
from app.services.timetable_normalizer import NormalizedTimetableEntry


class TimetableConfidenceScorer:
    def score(self, entry: NormalizedTimetableEntry) -> NormalizedTimetableEntry:
        score = 100.0
        provenance = entry.normalized_json.get("provenance", {})

        if provenance.get("ocr_used"):
            score -= 10
            ocr_confidence = provenance.get("ocr_confidence")
            if ocr_confidence is not None:
                score -= max(0.0, (75.0 - float(ocr_confidence)) * 0.4)
        if not entry.template_name:
            score -= 15
        if not entry.class_name:
            score -= 25
        if not entry.academic_year:
            score -= 5
        if entry.warning:
            score -= 20
        if entry.validation_status == ValidationStatus.NEEDS_REVIEW:
            score = min(score, 69)
        elif entry.validation_status == ValidationStatus.INVALID:
            score = min(score, 39)

        entry.confidence_score = round(max(0.0, min(100.0, score)), 1)
        if entry.confidence_score >= 80:
            entry.confidence_level = ConfidenceLevel.HIGH
        elif entry.confidence_score >= 50:
            entry.confidence_level = ConfidenceLevel.MEDIUM
        else:
            entry.confidence_level = ConfidenceLevel.LOW
        if entry.confidence_level == ConfidenceLevel.LOW and entry.validation_status == ValidationStatus.VALID:
            entry.validation_status = ValidationStatus.NEEDS_REVIEW
            entry.warning = "Low-confidence extraction requires review."
        entry.normalized_json["confidence"] = {
            "score": entry.confidence_score,
            "level": entry.confidence_level.value,
        }
        return entry
