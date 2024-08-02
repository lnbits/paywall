from asyncio import Queue

from lnbits.core.models import Payment
from lnbits.tasks import register_invoice_listener

paid_invoices: dict[str, Queue] = {}


async def wait_for_paid_invoices():
    invoice_queue = Queue()
    register_invoice_listener(invoice_queue)

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if payment.extra.get("tag") != "paywall":
        return

    if payment.payment_hash in paid_invoices:
        await paid_invoices[payment.payment_hash].put(payment)
