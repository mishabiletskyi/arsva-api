import json
from datetime import date, datetime, timezone

from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.call_log import CallLog
from app.models.tenant import Tenant
from app.schemas.call_log import CallLogCreate, CallLogUpdate
from app.services.access_service import can_access_property, can_manage_property, is_platform_owner


def _parse_expected_payment_date(value: str | None) -> date | None:
    if not value:
        return None

    return date.fromisoformat(value.strip())


def _coerce_duration_seconds(value) -> int | None:
    if value in {None, ""}:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        return int(float(value))

    return None


def _get_first_value(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _resolve_tenant_for_vapi_payload(db: Session, payload: dict) -> Tenant | None:
    call_data = payload.get("call") if isinstance(payload.get("call"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    assistant_overrides = (
        payload.get("assistantOverrides")
        if isinstance(payload.get("assistantOverrides"), dict)
        else {}
    )
    assistant_metadata = (
        assistant_overrides.get("metadata")
        if isinstance(assistant_overrides.get("metadata"), dict)
        else {}
    )

    merged_metadata = {
        **assistant_metadata,
        **metadata,
    }

    tenant_id = _get_first_value(
        merged_metadata.get("tenant_id"),
        payload.get("tenant_id"),
        call_data.get("tenant_id"),
    )
    if tenant_id is not None:
        try:
            tenant = (
                db.query(Tenant)
                .filter(
                    Tenant.id == int(tenant_id),
                    Tenant.is_archived.is_(False),
                )
                .first()
            )
            if tenant is not None:
                return tenant
        except (TypeError, ValueError):
            pass

    tenant_external_id = _get_first_value(
        merged_metadata.get("tenant_external_id"),
        payload.get("tenant_external_id"),
        call_data.get("tenant_external_id"),
    )
    if tenant_external_id is not None:
        tenant = (
            db.query(Tenant)
            .filter(
                Tenant.external_id == str(tenant_external_id),
                Tenant.is_archived.is_(False),
            )
            .first()
        )
        if tenant is not None:
            return tenant

    customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
    phone_number = _get_first_value(
        merged_metadata.get("phone_number"),
        payload.get("phone_number"),
        call_data.get("phone_number"),
        customer.get("number"),
    )
    if phone_number is not None:
        return (
            db.query(Tenant)
            .filter(
                Tenant.phone_number == str(phone_number),
                Tenant.is_archived.is_(False),
            )
            .first()
        )

    return None


def _apply_call_log_values(
    call_log: CallLog,
    tenant: Tenant,
    *,
    vapi_call_id: str | None,
    call_outcome: str | None,
    script_version: str | None,
    transcript: str | None,
    recording_url: str | None,
    opt_out_detected: bool,
    expected_payment_date: date | None,
    duration_seconds: int | None,
    raw_payload: str,
) -> None:
    if call_outcome is not None and not isinstance(call_outcome, str):
        call_outcome = str(call_outcome)
    if transcript is not None and not isinstance(transcript, str):
        transcript = json.dumps(transcript, ensure_ascii=False)
    if recording_url is not None and not isinstance(recording_url, str):
        recording_url = str(recording_url)

    call_log.organization_id = tenant.organization_id
    call_log.property_id = tenant.property_id
    call_log.tenant_id = tenant.id
    call_log.vapi_call_id = vapi_call_id
    call_log.call_outcome = call_outcome
    call_log.script_version = script_version
    call_log.transcript = transcript
    call_log.recording_url = recording_url
    call_log.opt_out_detected = opt_out_detected
    call_log.expected_payment_date = expected_payment_date
    call_log.duration_seconds = duration_seconds
    call_log.raw_payload = raw_payload


def _can_read_call_log(db: Session, current_user: AdminUser, call_log: CallLog) -> bool:
    if is_platform_owner(db, current_user):
        return True

    return can_access_property(
        db=db,
        user=current_user,
        organization_id=call_log.organization_id,
        property_id=call_log.property_id,
    )


def _can_write_call_log(db: Session, current_user: AdminUser, call_log: CallLog) -> bool:
    if is_platform_owner(db, current_user):
        return True

    return can_manage_property(
        db=db,
        user=current_user,
        organization_id=call_log.organization_id,
        property_id=call_log.property_id,
    )


def get_call_logs(
    db: Session,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
    organization_id: int | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
) -> list[CallLog]:
    query = db.query(CallLog)

    if organization_id is not None:
        query = query.filter(CallLog.organization_id == organization_id)
    if property_id is not None:
        query = query.filter(CallLog.property_id == property_id)
    if tenant_id is not None:
        query = query.filter(CallLog.tenant_id == tenant_id)

    query = query.order_by(CallLog.created_at.desc())

    if is_platform_owner(db, current_user):
        return query.offset(skip).limit(limit).all()

    call_logs = query.all()
    scoped_call_logs = [
        item for item in call_logs if _can_read_call_log(db, current_user, item)
    ]
    return scoped_call_logs[skip : skip + limit]


def get_call_log_by_id(
    db: Session,
    call_log_id: int,
    current_user: AdminUser,
) -> CallLog | None:
    call_log = (
        db.query(CallLog)
        .filter(CallLog.id == call_log_id)
        .first()
    )

    if call_log is None:
        return None

    if not _can_read_call_log(db, current_user, call_log):
        return None

    return call_log


def create_call_log(
    db: Session,
    payload: CallLogCreate,
    current_user: AdminUser,
) -> CallLog:
    settings = get_settings()
    tenant = (
        db.query(Tenant)
        .filter(Tenant.id == payload.tenant_id)
        .first()
    )
    if tenant is None:
        raise ValueError("Tenant not found")

    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=tenant.organization_id,
        property_id=tenant.property_id,
    ):
        raise PermissionError("You do not have access to create call logs for this tenant")

    call_log = CallLog()
    _apply_call_log_values(
        call_log,
        tenant,
        vapi_call_id=payload.vapi_call_id,
        call_outcome=payload.call_outcome,
        script_version=payload.script_version or settings.current_script_version,
        transcript=payload.transcript,
        recording_url=payload.recording_url,
        opt_out_detected=payload.opt_out_detected,
        expected_payment_date=payload.expected_payment_date,
        duration_seconds=payload.duration_seconds,
        raw_payload=payload.raw_payload,
    )

    if payload.opt_out_detected:
        tenant.opt_out_flag = True
        tenant.opt_out_timestamp = datetime.now(timezone.utc)

    db.add(call_log)
    db.add(tenant)
    db.commit()
    db.refresh(call_log)

    return call_log


def update_call_log(
    db: Session,
    call_log: CallLog,
    payload: CallLogUpdate,
    current_user: AdminUser,
) -> CallLog:
    if not _can_write_call_log(db, current_user, call_log):
        raise PermissionError("You do not have access to update this call log")

    update_data = payload.model_dump(exclude_unset=True)

    if "opt_out_detected" in update_data and update_data["opt_out_detected"]:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.id == call_log.tenant_id)
            .first()
        )
        if tenant is not None:
            tenant.opt_out_flag = True
            tenant.opt_out_timestamp = datetime.now(timezone.utc)
            db.add(tenant)

    for field, value in update_data.items():
        setattr(call_log, field, value)

    db.add(call_log)
    db.commit()
    db.refresh(call_log)

    return call_log


def create_or_update_call_log_from_vapi_payload(
    db: Session,
    payload: dict,
) -> CallLog:
    settings = get_settings()
    tenant = _resolve_tenant_for_vapi_payload(db, payload)
    if tenant is None:
        raise ValueError("Unable to map VAPI callback to a tenant")

    call_data = payload.get("call") if isinstance(payload.get("call"), dict) else {}
    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    structured_data = (
        analysis.get("structuredData")
        if isinstance(analysis.get("structuredData"), dict)
        else (
            analysis.get("structured_data")
            if isinstance(analysis.get("structured_data"), dict)
            else {}
        )
    )

    vapi_call_id = _get_first_value(
        payload.get("vapi_call_id"),
        payload.get("call_id"),
        payload.get("id"),
        call_data.get("id"),
    )
    if vapi_call_id is None:
        raise ValueError("VAPI callback is missing call ID")

    expected_payment_date_raw = _get_first_value(
        payload.get("expected_payment_date"),
        analysis.get("expected_payment_date"),
    )
    expected_payment_date = None
    if expected_payment_date_raw is not None:
        try:
            expected_payment_date = _parse_expected_payment_date(str(expected_payment_date_raw))
        except ValueError:
            expected_payment_date = None

    try:
        duration_seconds = _coerce_duration_seconds(
            _get_first_value(
                payload.get("duration_seconds"),
                call_data.get("durationSeconds"),
                call_data.get("duration"),
            )
        )
    except (TypeError, ValueError):
        duration_seconds = None

    opt_out_detected = bool(
        _get_first_value(
            payload.get("opt_out_detected"),
            analysis.get("opt_out_detected"),
            analysis.get("optOutDetected"),
        )
    )

    call_log = (
        db.query(CallLog)
        .filter(CallLog.vapi_call_id == str(vapi_call_id))
        .first()
    )
    if call_log is None:
        call_log = CallLog()

    _apply_call_log_values(
        call_log,
        tenant,
        vapi_call_id=str(vapi_call_id),
        call_outcome=_get_first_value(
            structured_data.get("call_outcome"),
            payload.get("call_outcome"),
            payload.get("status"),
            analysis.get("summary"),
            analysis.get("outcome"),
            call_data.get("status"),
        ),
        script_version=_get_first_value(
            structured_data.get("script_version"),
            payload.get("script_version"),
            settings.current_script_version,
        ),
        transcript=_get_first_value(
            payload.get("transcript"),
            artifact.get("transcript"),
            artifact.get("messages"),
        ),
        recording_url=_get_first_value(
            payload.get("recording_url"),
            artifact.get("recordingUrl"),
            artifact.get("recording_url"),
        ),
        opt_out_detected=opt_out_detected,
        expected_payment_date=expected_payment_date,
        duration_seconds=duration_seconds,
        raw_payload=json.dumps(payload, ensure_ascii=False),
    )

    if opt_out_detected:
        tenant.opt_out_flag = True
        tenant.opt_out_timestamp = datetime.now(timezone.utc)
        db.add(tenant)

    db.add(call_log)
    db.commit()
    db.refresh(call_log)

    return call_log
