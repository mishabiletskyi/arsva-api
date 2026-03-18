import csv
import io
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.call_log import CallLog
from app.models.csv_import import CsvImport
from app.models.dashboard_task import DashboardTask
from app.models.tenant import Tenant
from app.services.access_service import (
    can_access_property,
    get_property_in_scope,
    is_platform_owner,
    resolve_organization_scope,
)
from app.services.storage_service import (
    build_report_blob_name,
    upload_bytes_to_blob,
)


def _normalize_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    start = (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        if date_from is not None
        else None
    )
    end = (
        datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        if date_to is not None
        else None
    )
    return start, end


def _filter_by_scope(items: list, current_user: AdminUser, db: Session) -> list:
    if is_platform_owner(db, current_user):
        return items

    return [
        item
        for item in items
        if can_access_property(
            db=db,
            user=current_user,
            organization_id=item.organization_id,
            property_id=item.property_id,
        )
    ]


def _build_csv(columns: list[str], rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def _resolve_report_scope(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None,
    property_id: int | None,
) -> tuple[int | None, int | None]:
    effective_organization_id = resolve_organization_scope(
        db=db,
        user=current_user,
        organization_id=organization_id,
    )

    if property_id is not None:
        property_obj = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=property_id,
            organization_id=None,
            require_manage=False,
        )
        effective_organization_id = property_obj.organization_id

    return effective_organization_id, property_id


def store_report_export_csv(
    *,
    report_file_name: str,
    content: str,
    organization_id: int | None,
    property_id: int | None,
) -> str:
    settings = get_settings()
    blob_name = build_report_blob_name(
        report_name=report_file_name,
        organization_id=organization_id,
        property_id=property_id,
    )
    upload_bytes_to_blob(
        container_name=settings.azure_blob_container_exports,
        blob_name=blob_name,
        data=content.encode("utf-8"),
        content_type="text/csv",
    )
    return blob_name


def export_tenants_csv(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    effective_organization_id, property_id = _resolve_report_scope(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    )
    start, end = _normalize_date_range(date_from, date_to)
    query = db.query(Tenant)
    if effective_organization_id is not None:
        query = query.filter(Tenant.organization_id == effective_organization_id)
    if property_id is not None:
        query = query.filter(Tenant.property_id == property_id)
    if start is not None:
        query = query.filter(Tenant.created_at >= start)
    if end is not None:
        query = query.filter(Tenant.created_at <= end)

    tenants = _filter_by_scope(query.order_by(Tenant.created_at.desc()).all(), current_user, db)
    rows = [
        {
            "id": item.id,
            "organization_id": item.organization_id,
            "property_id": item.property_id,
            "first_name": item.first_name,
            "last_name": item.last_name,
            "phone_number": item.phone_number,
            "days_late": item.days_late,
            "consent_status": item.consent_status,
            "opt_out_flag": item.opt_out_flag,
            "is_suppressed": item.is_suppressed,
            "is_archived": item.is_archived,
            "created_at": item.created_at.isoformat(),
        }
        for item in tenants
    ]
    return _build_csv(list(rows[0].keys()) if rows else [
        "id",
        "organization_id",
        "property_id",
        "first_name",
        "last_name",
        "phone_number",
        "days_late",
        "consent_status",
        "opt_out_flag",
        "is_suppressed",
        "is_archived",
        "created_at",
    ], rows)


def export_call_logs_csv(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    effective_organization_id, property_id = _resolve_report_scope(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    )
    start, end = _normalize_date_range(date_from, date_to)
    query = db.query(CallLog)
    if effective_organization_id is not None:
        query = query.filter(CallLog.organization_id == effective_organization_id)
    if property_id is not None:
        query = query.filter(CallLog.property_id == property_id)
    if start is not None:
        query = query.filter(CallLog.created_at >= start)
    if end is not None:
        query = query.filter(CallLog.created_at <= end)

    call_logs = _filter_by_scope(query.order_by(CallLog.created_at.desc()).all(), current_user, db)
    rows = [
        {
            "id": item.id,
            "organization_id": item.organization_id,
            "property_id": item.property_id,
            "tenant_id": item.tenant_id,
            "vapi_call_id": item.vapi_call_id,
            "call_outcome": item.call_outcome,
            "opt_out_detected": item.opt_out_detected,
            "expected_payment_date": item.expected_payment_date.isoformat() if item.expected_payment_date else None,
            "duration_seconds": item.duration_seconds,
            "sms_sent": item.sms_sent,
            "sms_status": item.sms_status,
            "sms_message_sid": item.sms_message_sid,
            "sms_sent_at": item.sms_sent_at.isoformat() if item.sms_sent_at else None,
            "created_at": item.created_at.isoformat(),
        }
        for item in call_logs
    ]
    return _build_csv(list(rows[0].keys()) if rows else [
        "id",
        "organization_id",
        "property_id",
        "tenant_id",
        "vapi_call_id",
        "call_outcome",
        "opt_out_detected",
        "expected_payment_date",
        "duration_seconds",
        "sms_sent",
        "sms_status",
        "sms_message_sid",
        "sms_sent_at",
        "created_at",
    ], rows)


def export_csv_imports_csv(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    effective_organization_id, property_id = _resolve_report_scope(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    )
    start, end = _normalize_date_range(date_from, date_to)
    query = db.query(CsvImport).filter(CsvImport.deleted_at.is_(None))
    if effective_organization_id is not None:
        query = query.filter(CsvImport.organization_id == effective_organization_id)
    if property_id is not None:
        query = query.filter(CsvImport.property_id == property_id)
    if start is not None:
        query = query.filter(CsvImport.created_at >= start)
    if end is not None:
        query = query.filter(CsvImport.created_at <= end)

    imports = _filter_by_scope(query.order_by(CsvImport.created_at.desc()).all(), current_user, db)
    rows = [
        {
            "id": item.id,
            "organization_id": item.organization_id,
            "property_id": item.property_id,
            "original_file_name": item.original_file_name,
            "status": item.status,
            "total_rows": item.total_rows,
            "imported_rows": item.imported_rows,
            "failed_rows": item.failed_rows,
            "created_at": item.created_at.isoformat(),
        }
        for item in imports
    ]
    return _build_csv(list(rows[0].keys()) if rows else [
        "id",
        "organization_id",
        "property_id",
        "original_file_name",
        "status",
        "total_rows",
        "imported_rows",
        "failed_rows",
        "created_at",
    ], rows)


def export_dashboard_tasks_csv(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    effective_organization_id, property_id = _resolve_report_scope(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    )
    start, end = _normalize_date_range(date_from, date_to)
    query = db.query(DashboardTask)
    if effective_organization_id is not None:
        query = query.filter(DashboardTask.organization_id == effective_organization_id)
    if property_id is not None:
        query = query.filter(DashboardTask.property_id == property_id)
    if start is not None:
        query = query.filter(DashboardTask.created_at >= start)
    if end is not None:
        query = query.filter(DashboardTask.created_at <= end)

    tasks = _filter_by_scope(query.order_by(DashboardTask.created_at.desc()).all(), current_user, db)
    rows = [
        {
            "id": item.id,
            "organization_id": item.organization_id,
            "property_id": item.property_id,
            "title": item.title,
            "note": item.note,
            "status": item.status,
            "created_by_admin_id": item.created_by_admin_id,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in tasks
    ]
    return _build_csv(list(rows[0].keys()) if rows else [
        "id",
        "organization_id",
        "property_id",
        "title",
        "note",
        "status",
        "created_by_admin_id",
        "created_at",
        "updated_at",
    ], rows)
