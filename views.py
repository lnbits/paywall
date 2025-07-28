from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_paywall
from .models import PublicPaywall

paywall_generic_router = APIRouter()


def paywall_renderer():
    return template_renderer(["paywall/templates"])


@paywall_generic_router.get("/")
async def index(request: Request, user: User = Depends(check_user_exists)):
    return paywall_renderer().TemplateResponse(
        "paywall/index.html", {"request": request, "user": user.json()}
    )


@paywall_generic_router.get("/{paywall_id}")
async def display(request: Request, paywall_id: str):
    paywall = await get_paywall(paywall_id)
    if not paywall:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Paywall does not exist."
        )
    public_paywall = PublicPaywall(**paywall.dict())
    return paywall_renderer().TemplateResponse(
        "paywall/display.html", {"request": request, "paywall": public_paywall.json()}
    )
