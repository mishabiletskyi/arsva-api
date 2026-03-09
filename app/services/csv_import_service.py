import csv
import io
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.csv_import import CsvImport
from app.models.property import Property
from app.models.tenant import Tenant
from app.services.access_service import can_access_property, can_manage_property, is_platform_owner
from app.services.storage_service import (
    StorageServiceError,
    build_import_blob_name,
    upload_bytes_to_blob,
)


def _extract_error_field(message: str) -> str | None:
    if "first_name" in message:
        return "first_name"
    if "phone_number" in message:
        return "phone_number"
    if "external_id" in message:
        return "external_id"
    if "rent_due_date" in message:
        return "rent_due_date"
    if "days_late" in message:
        return "days_late"
    if "consent_timestamp" in message:
        return "consent_timestamp"
    if "consent_source" in message:
        return "consent_source"
    if "consent_document_version" in message:
        return "consent_document_version"
    return None


def _build_row_error(row_index: int, message: str) -> dict[str, int | str | None]:
    return {
        "row": row_index,
        "field": _extract_error_field(message),
        "message": message,
    }


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y"}


def _parse_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default

    return int(value)


def _parse_date(value: str | None) -> date | None:
    if value is None or value == "":
        return None

    return date.fromisoformat(value.strip())


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    return datetime.fromisoformat(normalized)


def get_csv_imports(
    db: Session,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
    organization_id: int | None = None,
    property_id: int | None = None,
) -> list[CsvImport]:
    query = db.query(CsvImport)

    if organization_id is not None:
        query = query.filter(CsvImport.organization_id == organization_id)
    if property_id is not None:
        query = query.filter(CsvImport.property_id == property_id)

    query = query.order_by(CsvImport.created_at.desc())

    if is_platform_owner(db, current_user):
        return query.offset(skip).limit(limit).all()

    imports = query.all()
    scoped_imports = [
        item
        for item in imports
        if can_access_property(
            db=db,
            user=current_user,
            organization_id=item.organization_id,
            property_id=item.property_id,
        )
    ]
    return scoped_imports[skip : skip + limit]


def get_csv_import_by_id(
    db: Session,
    csv_import_id: int,
    current_user: AdminUser,
) -> CsvImport | None:
    csv_import = (
        db.query(CsvImport)
        .filter(CsvImport.id == csv_import_id)
        .first()
    )

    if csv_import is None:
        return None

    if is_platform_owner(db, current_user):
        return csv_import

    if not can_access_property(
        db=db,
        user=current_user,
        organization_id=csv_import.organization_id,
        property_id=csv_import.property_id,
    ):
        return None

    return csv_import


def create_csv_import_from_upload(
    db: Session,
    current_user: AdminUser,
    organization_id: int,
    property_id: int,
    original_file_name: str,
    file_bytes: bytes,
) -> CsvImport:
    settings = get_settings()
    property_obj = (
        db.query(Property)
        .filter(Property.id == property_id)
        .first()
    )
    if property_obj is None:
        raise ValueError("Property not found")

    if property_obj.organization_id != organization_id:
        raise ValueError("organization_id does not match the selected property")

    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    ):
        raise PermissionError("You do not have access to import tenants into this property")

    stored_file_name = build_import_blob_name(
        organization_id=organization_id,
        property_id=property_id,
        original_file_name=original_file_name,
    )
    try:
        upload_bytes_to_blob(
            container_name=settings.azure_blob_container_uploads,
            blob_name=stored_file_name,
            data=file_bytes,
            content_type="text/csv",
        )
    except StorageServiceError as exc:
        raise ValueError(f"Failed to store CSV file in Azure Blob: {exc}") from exc

    csv_import = CsvImport(
        organization_id=organization_id,
        property_id=property_id,
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        status="processing",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
        error_message=None,
        uploaded_by_admin_id=current_user.id,
        errors=None,
    )
    db.add(csv_import)
    db.commit()
    db.refresh(csv_import)

    decoded_content = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded_content))

    total_rows = 0
    imported_rows = 0
    failed_rows = 0
    row_errors: list[str] = []
    structured_errors: list[dict[str, int | str | None]] = []
    seen_external_ids: set[str] = set()

    try:
        for row_index, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                with db.begin_nested():
                    first_name = (row.get("first_name") or "").strip()
                    phone_number = (row.get("phone_number") or "").strip()
                    external_id = (row.get("external_id") or "").strip() or None
                    should_track_external_id = False

                    if not first_name:
                        raise ValueError("first_name is required")
                    if not phone_number:
                        raise ValueError("phone_number is required")

                    if external_id:
                        if external_id in seen_external_ids:
                            raise ValueError("duplicate external_id in file")

                        existing_tenant = (
                            db.query(Tenant)
                            .filter(Tenant.external_id == external_id)
                            .first()
                        )
                        if existing_tenant is not None:
                            raise ValueError("external_id already exists")
                        should_track_external_id = True

                    try:
                        rent_due_date = _parse_date(row.get("rent_due_date"))
                    except ValueError:
                        raise ValueError("rent_due_date must be YYYY-MM-DD")

                    try:
                        days_late = _parse_int(row.get("days_late"), default=0)
                    except ValueError:
                        raise ValueError("days_late must be an integer")

                    try:
                        consent_timestamp = _parse_datetime(row.get("consent_timestamp"))
                    except ValueError:
                        raise ValueError("consent_timestamp must be ISO datetime")

                    try:
                        opt_out_timestamp = _parse_datetime(row.get("opt_out_timestamp"))
                    except ValueError:
                        raise ValueError("opt_out_timestamp must be ISO datetime")

                    tenant = Tenant(
                        organization_id=organization_id,
                        property_id=property_id,
                        external_id=external_id,
                        first_name=first_name,
                        last_name=(row.get("last_name") or "").strip() or None,
                        phone_number=phone_number,
                        property_name=(row.get("property_name") or "").strip() or property_obj.name,
                        timezone=(row.get("timezone") or "").strip() or property_obj.timezone,
                        rent_due_date=rent_due_date,
                        days_late=days_late,
                        consent_status=_parse_bool(row.get("consent_status"), default=False),
                        consent_timestamp=consent_timestamp,
                        consent_source=(row.get("consent_source") or "").strip() or None,
                        consent_document_version=(row.get("consent_document_version") or "").strip() or None,
                        opt_out_flag=_parse_bool(row.get("opt_out_flag"), default=False),
                        opt_out_timestamp=opt_out_timestamp,
                        eviction_status=_parse_bool(row.get("eviction_status"), default=False),
                        is_suppressed=_parse_bool(row.get("is_suppressed"), default=False),
                        notes=(row.get("notes") or "").strip() or None,
                    )
                    db.add(tenant)
                    db.flush()

                if external_id and should_track_external_id:
                    seen_external_ids.add(external_id)
                imported_rows += 1
            except Exception as exc:
                failed_rows += 1
                row_errors.append(f"row {row_index}: {exc}")
                structured_errors.append(_build_row_error(row_index, str(exc)))

        csv_import.total_rows = total_rows
        csv_import.imported_rows = imported_rows
        csv_import.failed_rows = failed_rows
        csv_import.status = "completed" if failed_rows == 0 else "completed_with_errors"
        csv_import.error_message = "\n".join(row_errors[:20]) or None
        csv_import.errors = structured_errors[:100] or None

        db.add(csv_import)
        db.commit()
        db.refresh(csv_import)

        return csv_import
    except Exception as exc:
        db.rollback()

        csv_import = (
            db.query(CsvImport)
            .filter(CsvImport.id == csv_import.id)
            .first()
        )
        if csv_import is not None:
            csv_import.status = "failed"
            csv_import.error_message = str(exc)
            csv_import.errors = [_build_row_error(0, str(exc))]
            db.add(csv_import)
            db.commit()
            db.refresh(csv_import)

        raise
