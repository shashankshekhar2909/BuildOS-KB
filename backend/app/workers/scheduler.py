from arq import cron
from arq.connections import RedisSettings
from app.config import settings
from app.workers.tasks import (
    discover_projects,
    extract_project,
    generate_okf,
    embed_document,
)


async def startup(ctx: dict) -> None:
    # ctx["redis"] is already the ARQ pool — no override needed
    pass


async def shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [
        discover_projects,
        extract_project,
        generate_okf,
        embed_document,
    ]
    cron_jobs = [
        cron(discover_projects, minute={0, 15, 30, 45}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
