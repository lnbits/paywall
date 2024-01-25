import json
from sqlite3 import Row
from typing import Optional

from fastapi import Query
from pydantic import BaseModel


class PaywallFileConfig(BaseModel):
    url: str
    headers: dict[str, str]
    # todo: nice to have:
    # expiration_time: Optional[int]
    # max_number_of_downloads: Optional[int]


class PaywallConfig(BaseModel):
    # possible types: 'url' and 'file'
    type: Optional[str] = "url"
    file_config: Optional[PaywallFileConfig]


class CreatePaywall(BaseModel):
    url: str = Query(...)
    memo: str = Query(...)
    description: str = Query(None)
    amount: int = Query(..., ge=0)
    remembers: bool = Query(...)
    extras: Optional[PaywallConfig] = None


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
    time: int
    remembers: bool
    extras: Optional[PaywallConfig] = PaywallConfig()

    @classmethod
    def from_row(cls, row: Row) -> "Paywall":
        data = dict(row)
        data["remembers"] = bool(data["remembers"])
        data["extras"] = PaywallConfig(**json.loads(data["extras"])) if data["extras"] else None
        return cls(**data)
