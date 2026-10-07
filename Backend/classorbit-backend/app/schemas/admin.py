from pydantic import BaseModel, Field


class TestDataResetRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class TestDataResetResponse(BaseModel):
    message: str
    deleted_counts: dict[str, int]
    total_deleted: int
    preserved_users: int

