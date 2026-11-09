import asyncio
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from lnbits.settings import settings
from lnbits.utils.safe_http import SafeHttpClient
from starlette.exceptions import HTTPException

from .. import views_api as views


@pytest.fixture
def anyio_backend():
    return "asyncio"


def paywall(url):
    return SimpleNamespace(
        memo="download",
        extras=SimpleNamespace(
            type="file",
            file_config=SimpleNamespace(url=url, headers={"X-API-KEY": "download-key"}),
        ),
    )


@pytest.mark.anyio
async def test_paid_file_url_cannot_read_server_file(monkeypatch, tmp_path):
    canary = tmp_path / "server-key"
    canary.write_text("private-canary")
    monkeypatch.setattr(
        views, "get_paywall", AsyncMock(return_value=paywall(canary.as_uri()))
    )
    monkeypatch.setattr(views, "_is_payment_made", AsyncMock(return_value=1000))
    with pytest.raises(HTTPException):
        await views.api_paywall_download_file("wall", payment_hash="paid")


@pytest.mark.anyio
async def test_unpaid_download_never_resolves_or_fetches(monkeypatch):
    monkeypatch.setattr(
        views,
        "get_paywall",
        AsyncMock(return_value=paywall("https://public.example/file")),
    )
    monkeypatch.setattr(views, "_is_payment_made", AsyncMock(return_value=0))
    validate = AsyncMock()
    monkeypatch.setattr(views, "validate_url", validate)
    with pytest.raises(HTTPException):
        await views.api_paywall_download_file("wall", payment_hash="unpaid")
    validate.assert_not_awaited()


@pytest.mark.anyio
async def test_paid_download_preserves_version_headers_and_streaming(monkeypatch):
    monkeypatch.setattr(settings, "lnbits_callback_url_rules", [])
    monkeypatch.setattr(
        views,
        "get_paywall",
        AsyncMock(return_value=paywall("https://public.example/{version}/file")),
    )
    monkeypatch.setattr(views, "_is_payment_made", AsyncMock(return_value=1000))
    monkeypatch.setattr(
        asyncio.get_running_loop(),
        "getaddrinfo",
        AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
            ]
        ),
    )
    seen = []

    def factory(**kwargs):
        client = SafeHttpClient(**kwargs)

        def handler(request):
            seen.append(request)
            return httpx.Response(200, content=b"download" * 200000)

        client.client._transport = httpx.MockTransport(handler)
        return client

    monkeypatch.setattr(views, "SafeHttpClient", factory)
    response = await views.api_paywall_download_file(
        "wall", version="v2", payment_hash="paid"
    )
    chunks = [chunk async for chunk in response.body_iterator]
    assert b"".join(chunks) == b"download" * 200000
    assert max(map(len, chunks)) <= 65536
    assert seen[0].url.path == "/v2/file"
    assert seen[0].headers["X-API-KEY"] == "download-key"
    assert response.headers["Content-Disposition"] == 'attachment; filename="download"'
