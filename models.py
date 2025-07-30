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
    amount: float = Query(..., ge=0)
    currency: Optional[str] = "sat"
    fiat_provider: Optional[str] = None
    remembers: bool = Query(...)
    extras: Optional[PaywallExtra] = None


class CreatePaywallInvoice(BaseModel):
    amount: float = Query(..., ge=0)
    pay_in_fiat: bool = Query(False)


class CheckPaywallInvoice(BaseModel):
    payment_hash: str = Query(...)


class PublicPaywall(BaseModel):
    id: str
    wallet: str
    url: str
    memo: str
    description: Optional[str]
    amount: float
    currency: str
    fiat_provider: Optional[str] = None
    remembers: bool
    time: datetime = datetime.now(timezone.utc)


class Paywall(PublicPaywall):
    extras: Optional[PaywallExtra] = PaywallExtra()
