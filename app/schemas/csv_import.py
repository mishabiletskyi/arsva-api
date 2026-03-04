from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CsvImportErrorDetail(BaseModel):
    row: int
    field: str | None = None
    message: str


class CsvImportResponse(BaseModel):
    id: int
    organization_id: int
    property_id: int
    original_file_name: str
    stored_file_name: str | None = None
    status: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    error_message: str | None = None
    errors: list[CsvImportErrorDetail] | None = None
    uploaded_by_admin_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
