import asyncio
import logging
from datetime import datetime, timedelta

from .ad_import import import_from_ad
from .config import settings
from .database import AsyncSessionLocal

log = logging.getLogger(__name__)

_sync_lock = asyncio.Lock()


def _parse_sync_times() -> list[tuple[int, int]]:
    """'HH:MM,HH:MM' -> [(hour, minute), ...], отсортировано."""
    times: set[tuple[int, int]] = set()
    for part in settings.ad_sync_times.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            h, m = part.split(":")
            times.add((int(h), int(m)))
        except ValueError:
            log.warning("AD_SYNC_TIMES: пропускаю некорректное время %r", part)
    return sorted(times)


def _next_run(now: datetime, times: list[tuple[int, int]]) -> datetime:
    for h, m in times:
        candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate > now:
            return candidate
    h, m = times[0]
    return (now + timedelta(days=1)).replace(
        hour=h, minute=m, second=0, microsecond=0
    )


async def run_sync(trigger: str) -> None:
    """Один проход синхронизации; ошибки глушатся, чтобы не убить цикл."""
    async with _sync_lock:
        try:
            async with AsyncSessionLocal() as db:
                result = await import_from_ad(db)
            log.info("AD sync (%s): %s", trigger, result)
        except Exception:
            log.exception("AD sync (%s) завершился ошибкой", trigger)


async def _scheduler_loop() -> None:
    times = _parse_sync_times()
    if not times:
        log.warning("AD_SYNC_TIMES пуст — плановая синхронизация отключена")
        return
    log.info(
        "AD sync scheduler запущен, расписание: %s",
        ", ".join(f"{h:02d}:{m:02d}" for h, m in times),
    )
    while True:
        now = datetime.now()
        delay = (_next_run(now, times) - now).total_seconds()
        await asyncio.sleep(delay)
        await run_sync("scheduler")


def start_scheduler() -> asyncio.Task | None:
    if not settings.ad_sync_enabled:
        log.info("AD sync scheduler отключён (AD_SYNC_ENABLED=false)")
        return None
    return asyncio.create_task(_scheduler_loop())
