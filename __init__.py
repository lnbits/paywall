import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import paywall_generic_router
from .views_api import paywall_api_router

paywall_ext: APIRouter = APIRouter(prefix="/paywall", tags=["Paywall"])
paywall_ext.include_router(paywall_generic_router)
paywall_ext.include_router(paywall_api_router)

paywall_static_files = [
    {
        "path": "/paywall/static",
        "name": "paywall_static",
    }
]
scheduled_tasks: list[asyncio.Task] = []


def paywall_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def paywall_start():
    task = create_permanent_unique_task("ext_paywall", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = ["db", "paywall_ext", "paywall_static_files", "paywall_start", "paywall_stop"]
