"""
Adapter Layer — Proxy to CF Workers v1 (Wrap & Modernize pattern, ADR-001).
For endpoints not yet migrated to v2.
"""

import httpx
from fastapi import Request, Response

from app.settings import settings


class CFAdapter:
    def __init__(self):
        self.base_url = settings.cf_adapter_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def proxy(self, request: Request, path: str) -> Response:
        """Forward request to CF Workers v1, converting cookie to Bearer token."""
        url = f"{self.base_url}/{path}"

        # Convert httpOnly cookie to Authorization header for v1
        token = request.cookies.get(settings.cookie_name)
        headers = dict(request.headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Remove host header to avoid conflicts
        headers.pop("host", None)

        body = await request.body()

        resp = await self.client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )

    async def close(self):
        await self.client.aclose()


cf_adapter = CFAdapter()
