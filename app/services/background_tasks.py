# Periodic jobs, run as plain asyncio tasks from the app lifespan.
#
# Why not APScheduler/Celery: two fixed-interval coroutines in a single
# Railway container don't justify a scheduler dependency or a worker dyno.
# If this ever scales past one API process, the limit-fill sweep is the one
# job that must move out (it would double-fire), and it's already isolated
# behind process_open_limit_orders().

import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.services.limit_order_worker import process_open_limit_orders
from app.services.portfolio_service import snapshot_all_accounts

logger = logging.getLogger(__name__)


async def _run_every(interval_seconds: int, job, job_name: str):
    while True:
        try:
            await job()
        except asyncio.CancelledError:
            raise
        except Exception:
            # a bad sweep must not kill the loop for the life of the process
            logger.exception("Background job %s failed; retrying next tick", job_name)
        await asyncio.sleep(interval_seconds)


def start_background_tasks() -> list[asyncio.Task]:
    return [
        asyncio.create_task(_run_every(
            settings.limit_order_poll_seconds,
            lambda: process_open_limit_orders(SessionLocal),
            "limit-order-fills",
        )),
        asyncio.create_task(_run_every(
            settings.snapshot_interval_seconds,
            lambda: snapshot_all_accounts(SessionLocal),
            "portfolio-snapshots",
        )),
    ]


async def stop_background_tasks(tasks: list[asyncio.Task]):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
