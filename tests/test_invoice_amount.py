from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.exceptions import HTTPException

from .. import views_api as views
from ..models import CreatePaywallInvoice, Paywall


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def invoice_route(monkeypatch):
    paywall = Paywall(
        id="paywall",
        wallet="wallet",
        url="https://example.com/content",
        memo="content",
        amount=100,
        currency="sat",
        remembers=False,
    )
    payment = SimpleNamespace(payment_hash="payment-hash", bolt11="invoice")
    create = AsyncMock(return_value=payment)
    monkeypatch.setattr(views, "get_paywall", AsyncMock(return_value=paywall))
    monkeypatch.setattr(views, "create_payment_request", create)
    return paywall, payment, create


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("currency", "pay_in_fiat"), [("sat", False), ("USD", False), ("USD", True)]
)
@pytest.mark.parametrize("amount", [1, 99.99])
async def test_invoice_below_minimum_is_rejected(
    invoice_route, currency, pay_in_fiat, amount
):
    paywall, _, create = invoice_route
    paywall.currency = currency
    paywall.fiat_provider = "stripe"

    with pytest.raises(HTTPException) as exc:
        await views.api_paywall_create_invoice(
            CreatePaywallInvoice(amount=amount, pay_in_fiat=pay_in_fiat), paywall.id
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == f"Minimum amount is {paywall.amount} {currency}."
    create.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("currency", "pay_in_fiat"), [("sat", False), ("USD", False), ("USD", True)]
)
@pytest.mark.parametrize("amount", [100, 150])
async def test_invoice_at_or_above_minimum_preserves_request(
    invoice_route, currency, pay_in_fiat, amount
):
    paywall, payment, create = invoice_route
    paywall.currency = currency
    paywall.fiat_provider = "stripe"

    result = await views.api_paywall_create_invoice(
        CreatePaywallInvoice(amount=amount, pay_in_fiat=pay_in_fiat), paywall.id
    )

    assert result is payment
    create.assert_awaited_once()
    assert create.await_args.kwargs["wallet_id"] == paywall.wallet
    data = create.await_args.kwargs["invoice_data"]
    assert data.amount == amount
    assert data.unit == currency
    assert data.fiat_provider == ("stripe" if pay_in_fiat else None)
    assert data.extra == {"tag": "paywall", "id": paywall.id}
