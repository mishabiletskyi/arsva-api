import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
import httpx

from app.core.config import get_settings


class StorageServiceError(Exception):
    pass


def _get_blob_service_client() -> BlobServiceClient:
    settings = get_settings()
    if not settings.azure_blob_connection_string:
        raise StorageServiceError("Azure Blob connection string is not configured")

    try:
        return BlobServiceClient.from_connection_string(
            settings.azure_blob_connection_string
        )
    except Exception as exc:
        raise StorageServiceError(f"Failed to initialize Blob service client: {exc}") from exc


def _normalize_file_name(file_name: str) -> str:
    name = Path(file_name).name.strip()
    if not name:
        return "file"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def build_import_blob_name(
    *,
    organization_id: int,
    property_id: int,
    original_file_name: str,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    normalized_file_name = _normalize_file_name(original_file_name)
    return (
        f"org-{organization_id}/property-{property_id}/imports/"
        f"{timestamp}_{normalized_file_name}"
    )


def build_report_blob_name(
    *,
    report_name: str,
    organization_id: int | None,
    property_id: int | None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scope_org = str(organization_id) if organization_id is not None else "all"
    scope_property = str(property_id) if property_id is not None else "all"
    normalized_report_name = _normalize_file_name(report_name)
    return (
        f"org-{scope_org}/property-{scope_property}/exports/"
        f"{timestamp}_{normalized_report_name}"
    )


def build_recording_blob_name(
    *,
    organization_id: int,
    property_id: int,
    tenant_id: int,
    vapi_call_id: str | None,
    source_url: str,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parsed = urlparse(source_url)
    source_name = _normalize_file_name(Path(parsed.path).name or "recording.wav")
    call_id = _normalize_file_name(vapi_call_id or "call")
    return (
        f"org-{organization_id}/property-{property_id}/recordings/"
        f"tenant-{tenant_id}/{timestamp}_{call_id}_{source_name}"
    )


def upload_bytes_to_blob(
    *,
    container_name: str,
    blob_name: str,
    data: bytes,
    content_type: str | None = None,
) -> str:
    try:
        blob_service_client = _get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass

        blob_client = container_client.get_blob_client(blob_name)
        kwargs = {"overwrite": True}
        if content_type:
            kwargs["content_settings"] = ContentSettings(content_type=content_type)
        blob_client.upload_blob(data, **kwargs)
        return blob_client.url
    except StorageServiceError:
        raise
    except Exception as exc:
        raise StorageServiceError(f"Blob upload failed: {exc}") from exc


def mirror_remote_file_to_blob(
    *,
    container_name: str,
    blob_name: str,
    source_url: str,
) -> str:
    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(source_url)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type")
            return upload_bytes_to_blob(
                container_name=container_name,
                blob_name=blob_name,
                data=response.content,
                content_type=content_type,
            )
    except httpx.HTTPStatusError as exc:
        response_text = (
            exc.response.text if exc.response is not None else "Unknown source response"
        )
        raise StorageServiceError(
            f"Failed to fetch remote file for Blob mirror: {response_text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise StorageServiceError(f"Remote file fetch failed: {exc}") from exc
