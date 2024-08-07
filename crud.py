import json
from typing import List, Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreatePaywall, Paywall

db = Database("ext_paywall")


async def create_paywall(wallet_id: str, data: CreatePaywall) -> Paywall:
    paywall_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO paywall.paywalls
        (id, wallet, url, memo, description, amount, remembers, extras)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paywall_id,
            wallet_id,
            data.url,
            data.memo,
            data.description,
            data.amount,
            int(data.remembers),
            json.dumps(data.extras.dict()) if data.extras else None,
        ),
    )

    paywall = await get_paywall(paywall_id)
    assert paywall, "Newly created paywall couldn't be retrieved"
    return paywall


async def update_paywall(
    paywall_id: str, wallet_id: str, data: CreatePaywall
) -> Paywall:
    await db.execute(
        """
        UPDATE paywall.paywalls
        SET (wallet, url, memo, description, amount, remembers, extras) =
        (?, ?, ?, ?, ?, ?, ?)
        WHERE id = ? AND wallet = ?
        """,
        (
            wallet_id,
            data.url,
            data.memo,
            data.description,
            data.amount,
            int(data.remembers),
            json.dumps(data.extras.dict()) if data.extras else None,
            paywall_id,
            wallet_id,
        ),
    )

    paywall = await get_paywall(paywall_id)
    assert paywall, "Updated paywall couldn't be retrieved"
    return paywall


async def get_paywall(paywall_id: str) -> Optional[Paywall]:
    row = await db.fetchone(
        "SELECT * FROM paywall.paywalls WHERE id = ?", (paywall_id,)
    )
    return Paywall.from_row(row) if row else None


async def get_paywalls(wallet_ids: Union[str, List[str]]) -> List[Paywall]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"SELECT * FROM paywall.paywalls WHERE wallet IN ({q})", (*wallet_ids,)
    )

    return [Paywall.from_row(row) for row in rows]


async def delete_paywall(paywall_id: str) -> None:
    await db.execute("DELETE FROM paywall.paywalls WHERE id = ?", (paywall_id,))
