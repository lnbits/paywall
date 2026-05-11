from datetime import datetime, timezone

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
    type: str | None = "url"
    file_config: PaywallFileConfig | None = None


class CreatePaywall(BaseModel):
    url: str = Query(...)
    memo: str = Query(...)
    description: str = Query(None)
    amount: float = Query(..., ge=0)
    currency: str | None = "sat"
    fiat_provider: str | None = None
    remembers: bool = Query(...)
    extras: PaywallExtra | None = None


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
    description: str | None
    amount: float
    currency: str
    fiat_provider: str | None = None
    remembers: bool
    time: datetime = datetime.now(timezone.utc)


class Paywall(PublicPaywall):
    extras: PaywallExtra | None = PaywallExtra()


class PublicPaywallPage(BaseModel):
    id: str
    memo: str
    description: str | None
    amount: float
    currency: str
    fiat_provider: str | None = None
