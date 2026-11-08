from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from lnbits.core.models import KeyType
from lnbits.decorators import require_invoice_key

from .. import views_api as views
from ..models import Paywall, PaywallExtra, PaywallFileConfig


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("all_wallets", [False, True])
async def test_list_headers_only_visible_with_admin_key(
    monkeypatch, admin, all_wallets
):
    stored = Paywall(
        id="paywall",
        wallet="wallet",
        url="https://example.com",
        memo="file",
        amount=1,
        currency="sat",
        remembers=False,
        extras=PaywallExtra(
            type="file",
            file_config=PaywallFileConfig(
                url="https://example.com/download",
                headers={
                    "Authorization": "Bearer private-canary",
                    "X-API-Key": "secret-canary",
                },
            ),
        ),
    )
    other = stored.model_copy(
        update={"id": "other", "wallet": "other-wallet"}, deep=True
    )
    rows = [stored, other] if all_wallets else [stored]
    listing = AsyncMock(return_value=rows)
    monkeypatch.setattr(views, "get_paywalls", listing)
    monkeypatch.setattr(
        views,
        "get_user",
        AsyncMock(return_value=SimpleNamespace(wallet_ids=["wallet", "other-wallet"])),
    )
    wallet_info = SimpleNamespace(
        key_type=KeyType.admin if admin else KeyType.invoice,
        wallet=SimpleNamespace(id="wallet", user="owner"),
    )
    app = FastAPI()
    app.include_router(views.paywall_api_router)
    app.dependency_overrides[require_invoice_key] = lambda: wallet_info
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/paywalls", params={"all_wallets": all_wallets}
        )
    assert response.status_code == 200
    listing.assert_awaited_once_with(
        ["wallet", "other-wallet"] if all_wallets else ["wallet"]
    )
    for row in response.json():
        assert row["extras"]["file_config"]["headers"] == (
            stored.extras.file_config.headers if admin else {}
        )
    if not admin:
        assert "private-canary" not in response.text
        assert "secret-canary" not in response.text
    # Redaction must never strip credentials needed by subsequent downloads.
    assert all(
        row.extras.file_config.headers["X-API-Key"] == "secret-canary" for row in rows
    )
