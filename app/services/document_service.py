"""
Document Service - routes documents to DataRoom NAS.
Replaces Cloudflare R2 completely (ADR-011).
Local filesystem fallback when DATAROOM_ENABLED=false (dev/test mode).
"""

import hashlib
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.settings import settings

LOCAL_STORAGE_ROOT = Path("/tmp/sygnode_documents")


@dataclass
class DocumentRef:
    storage_ref: str
    sha256_hash: str
    dataroom_id: str | None = None


class DataRoomUnavailable(Exception):
    pass


class DocumentService:
    """
    Enruta documentos al DataRoom en el NAS del cliente.
    Fallback a almacenamiento local cuando DATAROOM_ENABLED=false.
    """

    def __init__(self):
        self.dataroom_url = settings.dataroom_api_url
        self.api_key = settings.dataroom_api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    async def upload_document(
        self,
        file_bytes: bytes,
        filename: str,
        org_id: uuid.UUID,
        doc_type: str,
        parent_id: uuid.UUID,
        supplier_id: uuid.UUID | None = None,
    ) -> DocumentRef:
        """Upload document. Returns reference with path and SHA256."""
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        path = self._build_path(org_id, doc_type, parent_id, supplier_id, filename)

        if settings.dataroom_enabled and self.dataroom_url:
            try:
                response = await self.client.post(
                    f"{self.dataroom_url}/api/documents/upload",
                    headers={"X-API-Key": self.api_key},
                    files={"file": (filename, file_bytes)},
                    data={
                        "path": path,
                        "sha256": sha256,
                        "org_id": str(org_id),
                        "doc_type": doc_type,
                    },
                )
                response.raise_for_status()
                return DocumentRef(
                    storage_ref=path,
                    sha256_hash=sha256,
                    dataroom_id=response.json().get("document_id"),
                )
            except (httpx.HTTPError, httpx.ConnectError) as e:
                if not settings.r2_fallback_enabled:
                    raise DataRoomUnavailable(f"DataRoom no disponible: {e}")
                # Fall through to local storage

        # Local filesystem fallback (dev/test)
        local_path = LOCAL_STORAGE_ROOT / path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(file_bytes)

        return DocumentRef(storage_ref=path, sha256_hash=sha256)

    async def get_document_bytes(self, storage_ref: str) -> bytes:
        """Download document from DataRoom or local storage."""
        if settings.dataroom_enabled and self.dataroom_url:
            try:
                response = await self.client.get(
                    f"{self.dataroom_url}/api/documents/download",
                    headers={"X-API-Key": self.api_key},
                    params={"path": storage_ref},
                )
                response.raise_for_status()
                return response.content
            except (httpx.HTTPError, httpx.ConnectError) as e:
                raise DataRoomUnavailable(f"DataRoom no disponible: {e}")

        # Local filesystem fallback
        local_path = LOCAL_STORAGE_ROOT / storage_ref
        if local_path.exists():
            return local_path.read_bytes()

        raise DataRoomUnavailable(f"Documento no encontrado localmente: {storage_ref}")

    def _build_path(
        self,
        org_id: uuid.UUID,
        doc_type: str,
        parent_id: uuid.UUID,
        supplier_id: uuid.UUID | None,
        filename: str,
    ) -> str:
        ts = int(datetime.now(timezone.utc).timestamp())
        if doc_type == "rfq" and supplier_id:
            return f"{org_id}/rfqs/{parent_id}/{supplier_id}/{ts}-{filename}"
        elif doc_type == "po":
            return f"{org_id}/pos/{parent_id}/{uuid.uuid4()}-{filename}"
        elif doc_type == "intake":
            return f"{org_id}/intake/{parent_id}/{filename}"
        return f"{org_id}/other/{parent_id}/{ts}-{filename}"

    async def close(self):
        await self.client.aclose()


# Singleton
document_service = DocumentService()
