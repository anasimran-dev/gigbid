"""Background worker (E1): Arq on Redis. Scouting and all agent runs happen here, not in web requests.

Run:  arq worker.main.WorkerSettings

Idempotency: each queued run has a deterministic Arq job id, so the same job is never queued twice;
task_bid continues from the thread's checkpoint if one exists; marketplace writes carry
idempotency keys. A worker restart therefore never double-analyses or double-submits.
"""
import asyncio
import os

from arq import create_pool, cron
from arq.connections import RedisSettings

from agent import mcp_client
from agent.config import cfg
from apps.api import db, service

REDIS = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


async def enqueue(task: str, *args):
    pool = await create_pool(REDIS)
    job_id = f"{task}:" + ":".join(str(a) for a in args if isinstance(a, str))[:200]
    await pool.enqueue_job("run_task", task, *args, _job_id=job_id)


async def run_task(ctx, task: str, *args):
    await asyncio.to_thread(service.TASKS[task], *args)


async def scout_all(ctx):
    """Scheduled scouting for every user, then board sync. Queued jobs are retried once the
    marketplace is reachable again (recovery from degraded mode)."""
    for user in db.tenants():
        result = await asyncio.to_thread(service.scout, user)
        if not result.get("degraded") and mcp_client.status()["ok"]:
            await asyncio.to_thread(service.retry_queued, user)
            await asyncio.to_thread(service.sync_marketplace, user)


async def startup(ctx):
    db.init()


def _minutes() -> set[int]:
    return {0}


def _hours() -> set[int]:
    every = max(1, cfg()["marketplace"]["scout_interval_minutes"] // 60)
    return set(range(0, 24, every))


class WorkerSettings:
    functions = [run_task]
    cron_jobs = [cron(scout_all, hour=_hours(), minute=_minutes())]
    on_startup = startup
    redis_settings = REDIS
    max_tries = 3
    job_timeout = 600
