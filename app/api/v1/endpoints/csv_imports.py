from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.csv_import import CsvImportResponse
from app.services.csv_import_service import (
    create_csv_import_from_upload,
    get_csv_import_by_id,
    get_csv_imports,
)

router = APIRouter(prefix="/csv-imports")


@router.get("", response_model=list[CsvImportResponse], summary="Get CSV imports list")
def list_csv_imports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_csv_imports(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        organization_id=organization_id,
        property_id=property_id,
    )


@router.get("/{csv_import_id}", response_model=CsvImportResponse, summary="Get CSV import by ID")
def get_csv_import(
    csv_import_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    csv_import = get_csv_import_by_id(
        db=db,
        csv_import_id=csv_import_id,
        current_user=current_user,
    )

    if csv_import is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CSV import not found",
        )

    return csv_import


@router.post(
    "/upload",
    response_model=CsvImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload CSV and import tenants",
)
async def upload_csv_import(
    organization_id: int = Form(...),
    property_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file name is required",
        )

    try:
        file_bytes = await file.read()
        return create_csv_import_from_upload(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
            property_id=property_id,
            original_file_name=file.filename,
            file_bytes=file_bytes,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
