from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer

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


from .views import *  # noqa: F401,F403,E402
from .views_api import *  # noqa: F401,F403,E402
