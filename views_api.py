from http import HTTPStatus
from typing import Optional
from urllib import request

from fastapi import Depends, Query, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.services import check_transaction_status, create_invoice
from lnbits.decorators import WalletTypeInfo, get_key_type, require_admin_key

from . import paywall_ext
from .crud import (
    create_paywall,
    delete_paywall,
    get_paywall,
    get_paywalls,
    update_paywall,
)
from .models import CheckPaywallInvoice, CreatePaywall, CreatePaywallInvoice, Paywall


@paywall_ext.get("/api/v1/paywalls")
async def api_paywalls(
    wallet: WalletTypeInfo = Depends(get_key_type), all_wallets: bool = Query(False)
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return [paywall.dict() for paywall in await get_paywalls(wallet_ids)]


@paywall_ext.post("/api/v1/paywalls")
async def api_paywall_create(
    data: CreatePaywall, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    paywall = await create_paywall(wallet_id=wallet.wallet.id, data=data)
    return paywall.dict()


@paywall_ext.patch("/api/v1/paywalls/{id}")
@paywall_ext.put("/api/v1/paywalls/{id}")
async def api_paywall_update(
    id: str, data: CreatePaywall, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    paywall = await update_paywall(id=id, wallet_id=wallet.wallet.id, data=data)
    return paywall.dict()


@paywall_ext.delete("/api/v1/paywalls/{paywall_id}")
async def api_paywall_delete(
    paywall_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    paywall = await get_paywall(paywall_id)

    if not paywall:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Paywall does not exist."
        )

    if paywall.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your paywall."
        )

    await delete_paywall(paywall_id)
    return "", HTTPStatus.NO_CONTENT


@paywall_ext.post("/api/v1/paywalls/invoice/{paywall_id}")
async def api_paywall_create_invoice(data: CreatePaywallInvoice, paywall_id: str):
    paywall = await get_paywall(paywall_id)
    assert paywall
    if data.amount < paywall.amount:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Minimum amount is {paywall.amount} sat.",
        )
    try:
        amount = data.amount if data.amount > paywall.amount else paywall.amount
        payment_hash, payment_request = await create_invoice(
            wallet_id=paywall.wallet,
            amount=amount,
            memo=f"{paywall.memo}",
            extra={"tag": "paywall", "id": paywall.id},
        )
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))

    return {"payment_hash": payment_hash, "payment_request": payment_request}


@paywall_ext.post("/api/v1/paywalls/check_invoice/{paywall_id}")
async def api_paywal_check_invoice(
    request: Request, data: CheckPaywallInvoice, paywall_id: str
):
    paywall = await get_paywall(paywall_id)
    if not paywall:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Paywall does not exist."
        )
    is_paid = await _is_payment_made(paywall, data.payment_hash)

    url = (
        paywall.url
        or f"{request.base_url}paywall/download/{paywall.id}"
        + f"?payment_hash={data.payment_hash}&version=__your_version_here___"
    )

    if is_paid:
        return {"paid": True, "url": url, "remembers": paywall.remembers}

    return {"paid": False}


@paywall_ext.get("/download/{paywall_id}")
async def api_paywall_download_file(
    paywall_id: str, version: Optional[str] = None, payment_hash: Optional[str] = None
):
    try:
        assert payment_hash, "Payment hash is missing."

        paywall = await get_paywall(paywall_id)
        assert paywall, "Paywall does not exist."
        assert paywall.extras, "Paywall invalid."
        assert paywall.extras.type == "file", "Paywall has not file to be downloaded."

        file_config = paywall.extras.file_config
        assert file_config, "Cannot find file to download"

        is_paid = await _is_payment_made(paywall, payment_hash)

        assert is_paid, "Invoice not paid."
        logger.info(
            f"Downloading file for paywall '{paywall_id}'."
            + f" Payment hash: '{payment_hash}', version: '{version}'."
        )

        headers = {"Content-Disposition": f'attachment; filename="{paywall.memo}"'}
        if version:
            file_config.url = file_config.url.format(version=version)
        return StreamingResponse(
            content=_file_streamer(file_config.url, file_config.headers),
            headers=headers,
        )
    except AssertionError as e:
        raise HTTPException(HTTPStatus.BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(e)
        raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, "Cannot download file.")


async def _file_streamer(url, headers):
    with request.urlopen(request.Request(url=url, headers=headers)) as dl_file:
        yield dl_file.read()


async def _is_payment_made(paywall: Paywall, payment_hash: str):
    try:
        status = await check_transaction_status(paywall.wallet, payment_hash)
        is_paid = not status.pending
    except Exception:
        return False

    if is_paid:
        payment = await get_standalone_payment(
            checking_id_or_hash=payment_hash, incoming=True, wallet_id=paywall.wallet
        )
        assert payment, f"Payment not found for payment_hash: '{payment_hash}'."
        if payment.extra.get("tag", None) != "paywall":
            return False
        paywall_id = payment.extra.get("id", None)
        if paywall_id and paywall_id != paywall.id:
            return False
        await payment.set_pending(False)

        return True
    return False
