from datetime import date
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.models.tenant import Tenant


class SmsDispatchError(Exception):
    pass


def _build_payment_link(tenant: Tenant) -> str | None:
    settings = get_settings()
    base_url = settings.payment_portal_url.strip()
    if not base_url:
        return None

    query = urlencode(
        {
            "tenant_id": tenant.id,
            "property_id": tenant.property_id,
        }
    )
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query}"


def _build_sms_body(tenant: Tenant, expected_payment_date: date | None) -> str:
    property_name = tenant.property_name or "your property"
    payment_link = _build_payment_link(tenant)

    parts = [
        f"Hi {tenant.first_name}, this is the automated leasing assistant for {property_name}.",
    ]

    if expected_payment_date is not None:
        parts.append(
            f"Thanks for sharing your expected payment date: {expected_payment_date.isoformat()}."
        )

    if payment_link:
        parts.append(f"Payment link: {payment_link}")
    else:
        parts.append("Please contact your leasing office for payment options.")

    parts.append("Reply STOP to opt out.")
    return " ".join(parts)


def send_payment_follow_up_sms(
    *,
    tenant: Tenant,
    expected_payment_date: date | None = None,
) -> dict:
    settings = get_settings()

    if not settings.twilio_account_sid:
        raise SmsDispatchError("Twilio Account SID is not configured")
    if not settings.twilio_auth_token:
        raise SmsDispatchError("Twilio Auth Token is not configured")
    if not settings.twilio_from_phone_number:
        raise SmsDispatchError("Twilio sender phone number is not configured")

    body = _build_sms_body(tenant=tenant, expected_payment_date=expected_payment_date)
    endpoint = (
        f"{settings.twilio_api_base_url.rstrip('/')}/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "From": settings.twilio_from_phone_number,
                    "To": tenant.phone_number,
                    "Body": body,
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        response_text = (
            exc.response.text if exc.response is not None else "Unknown Twilio error"
        )
        raise SmsDispatchError(f"Twilio request failed: {response_text}") from exc
    except httpx.HTTPError as exc:
        raise SmsDispatchError(f"Twilio connection failed: {exc}") from exc
