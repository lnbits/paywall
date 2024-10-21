from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreatePaywall, Paywall

db = Database("ext_paywall")


async def create_paywall(wallet_id: str, data: CreatePaywall) -> Paywall:
    paywall_id = urlsafe_short_hash()
    paywall = Paywall(
        id=paywall_id,
        wallet=wallet_id,
        **data.dict(),
    )
    await db.insert("paywall.paywalls", paywall)
    return paywall


async def update_paywall(paywall: Paywall) -> Paywall:
    await db.update("paywall.paywalls", paywall)
    return paywall


async def get_paywall(paywall_id: str) -> Optional[Paywall]:
    return await db.fetchone(
        "SELECT * FROM paywall.paywalls WHERE id = :id",
        {"id": paywall_id},
        Paywall,
    )


async def get_paywalls(wallet_ids: Union[str, list[str]]) -> list[Paywall]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM paywall.paywalls WHERE wallet IN ({q})", model=Paywall
    )


async def delete_paywall(paywall_id: str) -> None:
    await db.execute("DELETE FROM paywall.paywalls WHERE id = :id", {"id": paywall_id})
