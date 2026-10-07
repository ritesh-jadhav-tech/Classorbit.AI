from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.security import verify_password
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.admin import TestDataResetRequest, TestDataResetResponse
from app.services.data_reset_service import reset_test_data


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/test-data/reset", response_model=TestDataResetResponse)
def reset_all_test_data(
    payload: TestDataResetRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(RoleName.ADMIN)),
) -> TestDataResetResponse:
    if get_settings().environment.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The temporary test-data reset is disabled in production.",
        )
    if not verify_password(payload.password, current_admin.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin password is incorrect.")

    deleted_counts, preserved_users = reset_test_data(db)
    return TestDataResetResponse(
        message="All test data was deleted. User accounts and roles were preserved.",
        deleted_counts=deleted_counts,
        total_deleted=sum(deleted_counts.values()),
        preserved_users=preserved_users,
    )

