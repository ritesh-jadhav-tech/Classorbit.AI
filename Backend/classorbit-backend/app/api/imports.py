from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import ImportStatus, RoleName
from app.models.import_record import FileImport, ImportReview
from app.models.user import User
from app.schemas.import_schemas import FileImportRead, ImportConfirmResponse, ImportReviewRead, ImportReviewUpdate
from app.services.import_service import ImportService


router = APIRouter(prefix="/imports", tags=["imports"])
service = ImportService()


@router.get("", response_model=list[FileImportRead])
def list_imports(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> list[FileImport]:
    return db.query(FileImport).order_by(FileImport.created_at.desc()).all()


@router.post("", response_model=FileImportRead, status_code=status.HTTP_201_CREATED)
async def upload_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
) -> FileImport:
    try:
        return await service.create_import_from_upload(db, file, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/standard", response_model=FileImportRead, status_code=status.HTTP_201_CREATED)
async def upload_standard_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
) -> FileImport:
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The ClassOrbit timetable import accepts .xlsx or .xlsm files only.",
        )
    try:
        return await service.create_import_from_upload(db, file, current_user, standard_only=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{import_id}", response_model=FileImportRead)
def get_import(
    import_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> FileImport:
    file_import = db.get(FileImport, import_id)
    if not file_import:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    return file_import


@router.get("/{import_id}/quality-report")
def import_quality_report(
    import_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> dict:
    file_import = db.get(FileImport, import_id)
    if not file_import:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    return {
        "import_id": file_import.id,
        "filename": file_import.original_filename,
        "status": file_import.status.value,
        "pages": file_import.page_count,
        "parser_version": file_import.parser_version,
        "sha256": file_import.sha256,
        **(file_import.summary_json or {}),
    }


@router.get("/{import_id}/trace")
def import_trace(
    import_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> dict:
    if not db.get(FileImport, import_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    records = (
        db.execute(
            select(ImportReview)
            .where(ImportReview.file_import_id == import_id)
            .order_by(ImportReview.source_page, ImportReview.source_sheet, ImportReview.source_row, ImportReview.source_column)
            .limit(min(max(limit, 1), 500))
        )
        .scalars()
        .all()
    )
    return {
        "import_id": import_id,
        "records": [
            {
                "review_id": record.id,
                "source": {
                    "page": record.source_page,
                    "sheet": record.source_sheet,
                    "row": record.source_row,
                    "column": record.source_column,
                    "cell": record.source_cell_reference,
                    "bounding_box": record.bounding_box_json,
                    "method": record.extraction_method,
                    "parser": record.parser_name,
                    "template": record.template_name,
                },
                "raw_cell_text": record.raw_cell_text,
                "raw_entry_text": record.raw_entry_text,
                "interpreted": {
                    "subject": record.subject_text,
                    "room": record.room_hint,
                    "subject_type": record.subject_type,
                    "session_type": record.session_type,
                    "delivery_mode": record.delivery_mode,
                    "day": record.day_of_week,
                    "start_time": record.start_time,
                    "end_time": record.end_time,
                },
                "confidence": {
                    "level": record.confidence_level.value,
                    "score": record.confidence_score,
                },
                "validation_status": record.validation_status.value,
                "warning": record.warning,
                "decisions": (record.normalized_json or {}).get("decisions", []),
            }
            for record in records
        ],
    }


@router.get("/{import_id}/review", response_model=list[ImportReviewRead])
def list_review_records(
    import_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> list[ImportReview]:
    if not db.get(FileImport, import_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    return (
        db.execute(select(ImportReview).where(ImportReview.file_import_id == import_id).order_by(ImportReview.created_at))
        .scalars()
        .all()
    )


@router.patch("/{import_id}/review/{review_id}", response_model=ImportReviewRead)
def update_review_record(
    import_id: str,
    review_id: str,
    payload: ImportReviewUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> ImportReview:
    review = db.get(ImportReview, review_id)
    if not review or review.file_import_id != import_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review record not found.")
    try:
        return service.update_review_record(db, review, changes=payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{import_id}/confirm", response_model=ImportConfirmResponse)
def confirm_import(
    import_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> ImportConfirmResponse:
    file_import = db.get(FileImport, import_id)
    if not file_import:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    if file_import.status == ImportStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed imports cannot be confirmed.")
    created, skipped, unresolved = service.confirm_import(db, file_import)
    db.refresh(file_import)
    return ImportConfirmResponse(
        import_id=file_import.id,
        created_entries=created,
        skipped_records=skipped,
        unresolved_review_records=unresolved,
        status=file_import.status,
    )
