import asyncio
import logging
from datetime import datetime, time, timedelta

from .ad_import import import_from_ad
from .config import settings
from .database import AsyncSessionLocal

log = logging.getLogger(__name__)


def _parse_sync_times() -> list[time]:
    times: set[time] = set()
    for part in filter(None, (p.strip() for p in settings.ad_sync_times.split(","))):
        try:
            times.add(datetime.strptime(part, "%H:%M").time())
        except ValueError:
            log.warning("AD_SYNC_TIMES: некорректное время %r пропущено", part)
    return sorted(times)


def _next_run(now: datetime, times: list[time]) -> datetime:
    for t in times:
        candidate = datetime.combine(now.date(), t)
        if candidate > now:
            return candidate
    return datetime.combine(now.date() + timedelta(days=1), times[0])


async def _sync() -> None:
    try:
        async with AsyncSessionLocal() as db:
            result = await import_from_ad(db)
        log.info("Плановая синхронизация AD: %s", result)
    except Exception:
        log.exception("Плановая синхронизация AD завершилась ошибкой")


async def _scheduler_loop(times: list[time]) -> None:
    while True:
        now = datetime.now()
        await asyncio.sleep((_next_run(now, times) - now).total_seconds())
        await _sync()


def start_scheduler() -> asyncio.Task | None:
    if not settings.ad_sync_enabled:
        log.info("Плановая синхронизация AD отключена (AD_SYNC_ENABLED=false)")
        return None
    times = _parse_sync_times()
    if not times:
        log.warning("AD_SYNC_TIMES пуст — плановая синхронизация отключена")
        return None
    log.info("Плановая синхронизация AD: %s", ", ".join(t.strftime("%H:%M") for t in times))
    return asyncio.create_task(_scheduler_loop(times))
