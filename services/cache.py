import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 120):
        self._data: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is not None:
            expires, value = entry
            if time.time() < expires:
                return value
            del self._data[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.time() + self._ttl, value)

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()


github_cache = TTLCache(ttl_seconds=120)
