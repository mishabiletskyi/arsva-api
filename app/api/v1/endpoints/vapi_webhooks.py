from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.call_log import CallLogResponse
from app.services.call_log_service import create_or_update_call_log_from_vapi_payload

router = APIRouter(prefix="/webhooks/vapi")


@router.post(
    "/calls",
    response_model=CallLogResponse,
    summary="Process VAPI call webhook",
)
def process_vapi_call_webhook(
    payload: dict[str, Any],
    x_vapi_secret: str | None = Header(default=None),
):
    settings = get_settings()

    if settings.vapi_webhook_secret and x_vapi_secret != settings.vapi_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid VAPI webhook secret",
        )

    db: Session = SessionLocal()
    try:
        try:
            return create_or_update_call_log_from_vapi_payload(
                db=db,
                payload=payload,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
    finally:
        db.close()
