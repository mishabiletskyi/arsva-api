from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.services.report_service import (
    export_call_logs_csv,
    export_csv_imports_csv,
    export_dashboard_tasks_csv,
    export_tenants_csv,
    store_report_export_csv,
)
from app.services.storage_service import StorageServiceError

router = APIRouter(prefix="/reports")


def _csv_response(filename: str, content: str, blob_path: str | None = None) -> Response:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if blob_path:
        headers["X-Report-Blob-Path"] = blob_path

    return Response(
        content=content,
        media_type="text/csv",
        headers=headers,
    )


@router.get("/tenants.csv", summary="Export tenants CSV")
def export_tenants_report(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    content = export_tenants_csv(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        blob_path = store_report_export_csv(
            report_file_name="tenants.csv",
            content=content,
            organization_id=organization_id,
            property_id=property_id,
        )
    except StorageServiceError:
        blob_path = None

    return _csv_response("tenants.csv", content, blob_path=blob_path)


@router.get("/call-logs.csv", summary="Export call logs CSV")
def export_call_logs_report(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    content = export_call_logs_csv(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        blob_path = store_report_export_csv(
            report_file_name="call-logs.csv",
            content=content,
            organization_id=organization_id,
            property_id=property_id,
        )
    except StorageServiceError:
        blob_path = None

    return _csv_response("call-logs.csv", content, blob_path=blob_path)


@router.get("/csv-imports.csv", summary="Export CSV imports report")
def export_csv_imports_report(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    content = export_csv_imports_csv(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        blob_path = store_report_export_csv(
            report_file_name="csv-imports.csv",
            content=content,
            organization_id=organization_id,
            property_id=property_id,
        )
    except StorageServiceError:
        blob_path = None

    return _csv_response("csv-imports.csv", content, blob_path=blob_path)


@router.get("/dashboard-tasks.csv", summary="Export dashboard tasks report")
def export_dashboard_tasks_report(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    content = export_dashboard_tasks_csv(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        blob_path = store_report_export_csv(
            report_file_name="dashboard-tasks.csv",
            content=content,
            organization_id=organization_id,
            property_id=property_id,
        )
    except StorageServiceError:
        blob_path = None

    return _csv_response("dashboard-tasks.csv", content, blob_path=blob_path)
