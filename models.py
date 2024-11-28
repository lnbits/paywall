from datetime import datetime, timezone
from typing import Optional

from fastapi import Query
from pydantic import BaseModel


class PaywallFileConfig(BaseModel):
    url: str
    headers: dict[str, str]
    # todo: nice to have:
    # expiration_time: Optional[int]
    # max_number_of_downloads: Optional[int]


class PaywallExtra(BaseModel):
    # possible types: 'url' and 'file'
    type: Optional[str] = "url"
    file_config: Optional[PaywallFileConfig] = None


class CreatePaywall(BaseModel):
    url: str = Query(...)
    memo: str = Query(...)
    description: str = Query(None)
    amount: int = Query(..., ge=0)
    remembers: bool = Query(...)
    extras: Optional[PaywallExtra] = None


class CreatePaywallInvoice(BaseModel):
    amount: int = Query(..., ge=1)


class CheckPaywallInvoice(BaseModel):
    payment_hash: str = Query(...)


class Paywall(BaseModel):
    id: str
    wallet: str
    url: str
    memo: str
    description: Optional[str]
    amount: int
    remembers: bool
    time: datetime = datetime.now(timezone.utc)
    extras: Optional[PaywallExtra] = PaywallExtra()
