import time
from collections import deque


class SlidingWindowLimiter:
    """Счётчик событий в скользящем окне, хранится в памяти процесса.

    При нескольких воркерах uvicorn у каждого свой счётчик — лимиты
    фактически умножаются на число воркеров.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()

    def _prune(self, key: str, now: float) -> deque[float] | None:
        q = self._events.get(key)
        if q is None:
            return None
        while q and q[0] <= now - self.window:
            q.popleft()
        if not q:
            del self._events[key]
            return None
        return q

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self.window:
            return
        self._last_cleanup = now
        for key in list(self._events):
            self._prune(key, now)

    def retry_after(self, key: str) -> int:
        """0 — можно продолжать, иначе через сколько секунд повторить."""
        now = time.monotonic()
        self._cleanup(now)
        q = self._prune(key, now)
        if q is None or len(q) < self.limit:
            return 0
        return max(1, int(q[0] + self.window - now) + 1)

    def hit(self, key: str) -> None:
        self._events.setdefault(key, deque()).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._events.pop(key, None)
