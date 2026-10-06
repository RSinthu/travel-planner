"""Per-user rate limit for chat messages.

Every planning message costs ~10 Gemini requests, so this protects the quota
(and the bill) from one user or a stuck client. It keeps counts in memory, so it
is per server process: with several processes, move it to Redis.
"""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_minute: int, per_day: int, clock=time.monotonic):
        self.windows = ((60.0, per_minute), (86_400.0, per_day))
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, user_id: str) -> float | None:
        """Record a hit and return None, or return seconds to wait if over a limit."""
        now = self.clock()
        hits = self.hits[user_id]
        longest = max(seconds for seconds, _ in self.windows)
        while hits and now - hits[0] >= longest:
            hits.popleft()
        for seconds, limit in self.windows:
            recent = [t for t in hits if now - t < seconds]
            if len(recent) >= limit:
                return max(seconds - (now - recent[0]), 1.0)
        hits.append(now)
        return None
