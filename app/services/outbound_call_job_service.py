import json

from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.outbound_call_job import OutboundCallJob
from app.models.tenant import Tenant
from app.schemas.outbound_call_job import OutboundCallJobCreate
from app.services.call_log_service import create_or_get_call_log_for_dispatch
from app.services.call_policy_service import build_policy_snapshot, get_effective_call_policy_map
from app.services.access_service import (
    can_access_property,
    can_manage_property,
    get_property_in_scope,
    is_platform_owner,
    resolve_organization_scope,
)
from app.services.compliance_service import evaluate_tenant_eligibility
from app.services.vapi_service import VapiDispatchError, create_outbound_call


def _build_job_note(
    *,
    dry_run: bool,
    started_count: int,
    failed_count: int,
    blocked_count: int,
) -> str:
    if dry_run:
        return "Preview only; no outbound calls sent."
    if started_count > 0:
        if failed_count > 0:
            return "Outbound calls started, but some requests failed."
        return "Outbound calls started."
    if failed_count > 0:
        return "Outbound call dispatch failed."
    if blocked_count > 0:
        return "No calls started because selected tenants were blocked by policy."
    return "No calls were started."


def get_outbound_call_jobs(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
) -> list[OutboundCallJob]:
    effective_organization_id = resolve_organization_scope(
        db=db,
        user=current_user,
        organization_id=organization_id,
    )

    if property_id is not None:
        scoped_property = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=property_id,
            organization_id=None,
            require_manage=False,
        )
        effective_organization_id = scoped_property.organization_id

    query = db.query(OutboundCallJob)

    if effective_organization_id is not None:
        query = query.filter(OutboundCallJob.organization_id == effective_organization_id)
    if property_id is not None:
        query = query.filter(OutboundCallJob.property_id == property_id)

    jobs = query.order_by(OutboundCallJob.created_at.desc()).all()

    if is_platform_owner(db, current_user):
        return jobs

    return [
        job
        for job in jobs
        if (
            job.organization_id is None
            or job.property_id is None
            or can_access_property(
                db=db,
                user=current_user,
                organization_id=job.organization_id,
                property_id=job.property_id,
            )
        )
    ]


def get_outbound_call_job_by_id(
    db: Session,
    job_id: int,
    current_user: AdminUser,
) -> OutboundCallJob | None:
    job = (
        db.query(OutboundCallJob)
        .filter(OutboundCallJob.id == job_id)
        .first()
    )
    if job is None:
        return None

    if is_platform_owner(db, current_user):
        return job

    if job.organization_id is None or job.property_id is None:
        return None

    if not can_access_property(
        db=db,
        user=current_user,
        organization_id=job.organization_id,
        property_id=job.property_id,
    ):
        return None

    return job


def create_outbound_call_job(
    db: Session,
    payload: OutboundCallJobCreate,
    current_user: AdminUser,
) -> OutboundCallJob:
    settings = get_settings()
    effective_organization_id = resolve_organization_scope(
        db=db,
        user=current_user,
        organization_id=None,
    )

    if payload.property_id is not None:
        property_obj = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=payload.property_id,
            organization_id=None,
            require_manage=True,
        )
        effective_organization_id = property_obj.organization_id

    query = db.query(Tenant).filter(Tenant.is_archived.is_(False))

    if effective_organization_id is not None:
        query = query.filter(Tenant.organization_id == effective_organization_id)
    if payload.property_id is not None:
        query = query.filter(Tenant.property_id == payload.property_id)
    if payload.tenant_ids:
        query = query.filter(Tenant.id.in_(payload.tenant_ids))

    tenants = query.order_by(Tenant.created_at.desc()).all()

    manageable_tenants = [
        tenant
        for tenant in tenants
        if can_manage_property(
            db=db,
            user=current_user,
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
        )
    ]

    if payload.tenant_ids and len(manageable_tenants) != len(set(payload.tenant_ids)):
        raise PermissionError("One or more selected tenants are not manageable in your scope")

    if not manageable_tenants:
        raise PermissionError("No eligible scope found for outbound call job creation")

    effective_limit = payload.max_tenants or settings.pilot_max_batch_size
    effective_limit = min(effective_limit, settings.pilot_max_batch_size)
    manageable_tenants = manageable_tenants[:effective_limit]

    scopes = {(tenant.organization_id, tenant.property_id) for tenant in manageable_tenants}
    policy_map = get_effective_call_policy_map(db=db, scopes=scopes)

    eligibility_results = [
        evaluate_tenant_eligibility(
            db=db,
            tenant=tenant,
            policy=policy_map[(tenant.organization_id, tenant.property_id)],
        )
        for tenant in manageable_tenants
    ]
    eligible_results = [item for item in eligibility_results if item["can_call_now"]]
    blocked_results = [item for item in eligibility_results if not item["can_call_now"]]

    assistant_id = (payload.assistant_id or settings.vapi_default_assistant_id).strip()
    phone_number_id = (payload.phone_number_id or settings.vapi_phone_number_id).strip()

    if not payload.dry_run:
        if not assistant_id:
            raise ValueError("assistant_id is required when dry_run is false")
        if not phone_number_id:
            raise ValueError("phone_number_id is required when dry_run is false")

    dispatched_calls: list[dict] = []
    dispatch_errors: list[dict] = []

    if not payload.dry_run:
        eligible_tenants_by_id = {
            item["tenant_id"]: next(
                tenant for tenant in manageable_tenants if tenant.id == item["tenant_id"]
            )
            for item in eligible_results
        }

        for tenant_id, tenant in eligible_tenants_by_id.items():
            try:
                vapi_response = create_outbound_call(
                    tenant=tenant,
                    assistant_id=assistant_id,
                    phone_number_id=phone_number_id,
                )
                vapi_call_id = vapi_response.get("id")
                if isinstance(vapi_call_id, str) and vapi_call_id:
                    create_or_get_call_log_for_dispatch(
                        db=db,
                        tenant=tenant,
                        vapi_call_id=vapi_call_id,
                        script_version=settings.current_script_version,
                        call_status=str(vapi_response.get("status") or "queued"),
                        raw_payload=json.dumps(vapi_response, ensure_ascii=False),
                    )
                dispatched_calls.append(
                    {
                        "tenant_id": tenant_id,
                        "phone_number": tenant.phone_number,
                        "vapi_response": vapi_response,
                    }
                )
            except VapiDispatchError as exc:
                dispatch_errors.append(
                    {
                        "tenant_id": tenant_id,
                        "phone_number": tenant.phone_number,
                        "error": str(exc),
                    }
                )

    requested_count = len(eligibility_results)
    started_count = len(dispatched_calls)
    failed_count = len(dispatch_errors)
    blocked_count = len(blocked_results)
    note = _build_job_note(
        dry_run=payload.dry_run,
        started_count=started_count,
        failed_count=failed_count,
        blocked_count=blocked_count,
    )

    job = OutboundCallJob(
        organization_id=effective_organization_id,
        property_id=payload.property_id,
        status=(
            "previewed"
            if payload.dry_run
            else ("queued" if started_count > 0 else "failed")
        ),
        trigger_mode=payload.trigger_mode.strip().lower(),
        dry_run=payload.dry_run,
        requested_by_admin_id=current_user.id,
        total_candidates=requested_count,
        eligible_count=len(eligible_results),
        blocked_count=blocked_count,
        filters={
            "organization_id": effective_organization_id,
            "property_id": payload.property_id,
            "tenant_ids": payload.tenant_ids,
            "assistant_id": assistant_id or None,
            "phone_number_id": phone_number_id or None,
            "max_tenants": payload.max_tenants,
            "effective_max_tenants": effective_limit,
        },
        policy_snapshot=build_policy_snapshot(
            [policy_map[scope] for scope in sorted(scopes, key=lambda item: (item[0], item[1]))]
        ),
        result_summary={
            "requested_count": requested_count,
            "started_count": started_count,
            "failed_count": failed_count,
            "note": note,
            "dispatched_calls": dispatched_calls,
            "dispatch_errors": dispatch_errors,
        },
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job
