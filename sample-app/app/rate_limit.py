"""토큰 버킷 기반 요청 제한기.

외부 인증 서버가 429를 돌려주기 전에 우리 쪽에서 먼저 흘려보낸다.
"""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(
        self,
        capacity: float = 20.0,
        refill_per_sec: float = 5.0,
        now=time.monotonic,
    ) -> None:
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self._now = now
        self._tokens = capacity
        self._updated_at = now()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        elapsed = self._now() - self._updated_at
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_sec)
        self._updated_at = self._now()

    def try_acquire(self, cost: float = 1.0) -> bool:
        """허용되면 True. 버킷이 비었으면 False."""
        self._refill()
        if self._tokens < cost:
            return False
        self._tokens -= cost
        return True

    async def acquire(self, cost: float = 1.0) -> None:
        """버킷이 찰 때까지 기다린 뒤 통과시킨다."""
        async with self._lock:
            while not self.try_acquire(cost):
                deficit = cost - self._tokens
                await asyncio.sleep(deficit / self.refill_per_sec)
