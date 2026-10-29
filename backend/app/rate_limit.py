import threading
import time
from collections import deque


class LoginRateLimiter:
    """Счётчик неудачных попыток входа в скользящем окне (в памяти процесса)."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures.get(key)
        if q is None:
            return deque()
        while q and now - q[0] >= self.window_seconds:
            q.popleft()
        if not q:
            del self._failures[key]
        return q

    def retry_after(self, key: str, limit: int | None = None) -> int:
        """Сколько секунд ждать до следующей попытки; 0 — можно пробовать."""
        limit = limit or self.max_attempts
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) < limit:
                return 0
            return max(1, int(self.window_seconds - (now - q[0])) + 1)

    def add_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()
