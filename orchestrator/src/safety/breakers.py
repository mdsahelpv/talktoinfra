"""Circuit breakers — token budgets, rate limiters, cost caps, and circuit states."""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class TokenBudget:
    limit: int
    _used: int = 0

    def consume(self, tokens: int) -> bool:
        if self._used + tokens > self.limit:
            return False
        self._used += tokens
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self._used)

    @property
    def exhausted(self) -> bool:
        return self._used >= self.limit


@dataclass
class RateLimiter:
    max_calls: int
    window_seconds: float
    _calls: deque = field(default_factory=deque)

    def allow(self) -> bool:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self.window_seconds:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True

    @property
    def remaining(self) -> int:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self.window_seconds:
            self._calls.popleft()
        return max(0, self.max_calls - len(self._calls))


@dataclass
class MaxIterationsGuard:
    max_iterations: int

    def check(self, current: int) -> bool:
        return current <= self.max_iterations


@dataclass
class CostCap:
    max_cost: float
    _total: float = 0.0

    def record(self, cost: float) -> bool:
        self._total += cost
        if self._total > self.max_cost:
            return False
        return True

    @property
    def total(self) -> float:
        return self._total

    @property
    def exceeded(self) -> bool:
        return self._total > self.max_cost


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    async def call_async(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after %d failures", self._failure_count)

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
