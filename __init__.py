import asyncio
from typing import List
from fastapi import APIRouter
from asyncio import Queue, Task

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import catch_everything_and_restart

db = Database("ext_paywall")

paywall_ext: APIRouter = APIRouter(prefix="/paywall", tags=["Paywall"])

paywall_static_files = [
    {
        "path": "/paywall/static",
        "name": "paywall_static",
    }
]


def paywall_renderer():
    return template_renderer(["paywall/templates"])


scheduled_tasks: List[Task] = []


from .tasks import wait_for_paid_invoices, paid_invoices  # noqa: F401,F403,E402
from .views import *  # noqa: F401,F403,E402
from .views_api import *  # noqa: F401,F403,E402


def paywall_start():
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(catch_everything_and_restart(wait_for_paid_invoices))
    scheduled_tasks.append(task1)
