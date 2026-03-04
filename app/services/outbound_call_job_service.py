from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.outbound_call_job import OutboundCallJob
from app.models.tenant import Tenant
from app.schemas.outbound_call_job import OutboundCallJobCreate
from app.services.access_service import can_access_property, can_manage_property, is_platform_owner
from app.services.compliance_service import evaluate_tenant_eligibility
from app.services.vapi_service import VapiDispatchError, create_outbound_call


def get_outbound_call_jobs(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
) -> list[OutboundCallJob]:
    query = db.query(OutboundCallJob)

    if organization_id is not None:
        query = query.filter(OutboundCallJob.organization_id == organization_id)
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
    query = db.query(Tenant).filter(Tenant.is_archived.is_(False))

    if payload.organization_id is not None:
        query = query.filter(Tenant.organization_id == payload.organization_id)
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

    eligibility_results = [
        evaluate_tenant_eligibility(db, tenant)
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

    job = OutboundCallJob(
        organization_id=payload.organization_id,
        property_id=payload.property_id,
        status=(
            "previewed"
            if payload.dry_run
            else ("failed" if dispatch_errors and not dispatched_calls else "queued")
        ),
        trigger_mode=payload.trigger_mode.strip().lower(),
        dry_run=payload.dry_run,
        requested_by_admin_id=current_user.id,
        total_candidates=len(eligibility_results),
        eligible_count=len(eligible_results),
        blocked_count=len(blocked_results),
        filters={
            "organization_id": payload.organization_id,
            "property_id": payload.property_id,
            "tenant_ids": payload.tenant_ids,
            "assistant_id": assistant_id or None,
            "phone_number_id": phone_number_id or None,
            "max_tenants": payload.max_tenants,
            "effective_max_tenants": effective_limit,
        },
        result_summary={
            "eligible_tenant_ids": [item["tenant_id"] for item in eligible_results],
            "blocked": [
                {
                    "tenant_id": item["tenant_id"],
                    "blocked_reasons": item["blocked_reasons"],
                }
                for item in blocked_results[:100]
            ],
            "dispatch_ready": not payload.dry_run,
            "dispatch_note": (
                "Preview only; no outbound calls sent."
                if payload.dry_run
                else (
                    "Outbound calls sent to VAPI."
                    if dispatched_calls
                    else "VAPI dispatch failed."
                )
            ),
            "dispatched_calls": dispatched_calls,
            "dispatch_errors": dispatch_errors,
        },
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job
