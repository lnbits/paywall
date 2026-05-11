from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from lnbits.core.views.generic import index, index_public
from lnbits.decorators import check_user_exists

from .crud import get_paywall

paywall_generic_router = APIRouter()

paywall_generic_router.add_api_route(
    "/", methods=["GET"], endpoint=index, dependencies=[Depends(check_user_exists)]
)


async def display(request: Request, paywall_id: str):
    paywall = await get_paywall(paywall_id)
    if not paywall:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Paywall does not exist."
        )
    return await index_public(request)


paywall_generic_router.add_api_route("/{paywall_id}", methods=["GET"], endpoint=display)
