import httpx

from app.core.config import get_settings
from app.models.tenant import Tenant


class VapiDispatchError(Exception):
    pass


def create_outbound_call(
    tenant: Tenant,
    *,
    assistant_id: str,
    phone_number_id: str,
) -> dict:
    settings = get_settings()

    if not settings.vapi_private_api_key:
        raise VapiDispatchError("VAPI private API key is not configured")

    payload = {
        "assistantId": assistant_id,
        "phoneNumberId": phone_number_id,
        "customer": {
            "number": tenant.phone_number,
        },
        "assistantOverrides": {
            "metadata": {
                "tenant_id": tenant.id,
                "tenant_external_id": tenant.external_id,
                "phone_number": tenant.phone_number,
                "organization_id": tenant.organization_id,
                "property_id": tenant.property_id,
            }
        },
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.vapi_api_base_url.rstrip('/')}/call",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.vapi_private_api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text if exc.response is not None else "Unknown VAPI error"
        raise VapiDispatchError(f"VAPI request failed: {response_text}") from exc
    except httpx.HTTPError as exc:
        raise VapiDispatchError(f"VAPI connection failed: {exc}") from exc
