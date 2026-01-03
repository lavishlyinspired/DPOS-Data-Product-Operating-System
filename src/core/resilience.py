"""
DPOS Resilience Module
Retry logic, circuit breakers, timeouts, and graceful degradation.
"""
import asyncio
import time
from datetime import datetime, timedelta, UTC
from typing import TypeVar, Callable, Optional, Any, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
import threading

from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 2       # Successes to close from half-open
    timeout_seconds: float = 30.0    # Time before trying half-open
    excluded_exceptions: tuple = ()  # Exceptions that don't count as failures


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Usage:
        breaker = CircuitBreaker("neo4j")

        @breaker
        def call_neo4j():
            ...
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, transitioning if needed."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = (datetime.now(UTC) - self._last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout_seconds:
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        logger.info(
                            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
                            extra={"circuit": self.name, "state": "half_open"}
                        )
            return self._state

    def _record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(
                        f"Circuit breaker '{self.name}' CLOSED after recovery",
                        extra={"circuit": self.name, "state": "closed"}
                    )
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _record_failure(self, exception: Exception):
        """Record a failed call."""
        if isinstance(exception, self.config.excluded_exceptions):
            return

        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(UTC)

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' OPENED (failed in half-open)",
                    extra={"circuit": self.name, "state": "open", "error": str(exception)}
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPENED (threshold reached)",
                        extra={
                            "circuit": self.name,
                            "state": "open",
                            "failures": self._failure_count,
                            "error": str(exception)
                        }
                    )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                raise

        return wrapper

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call a function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retry with exponential backoff.

    Usage:
        @retry(max_attempts=3, initial_delay=1.0)
        def flaky_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"Retry exhausted for {func.__name__} after {max_attempts} attempts",
                            extra={"function": func.__name__, "attempts": max_attempts, "error": str(e)}
                        )
                        raise

                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)
                    if jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}, waiting {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(e)
                        }
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for async retry with exponential backoff.

    Usage:
        @async_retry(max_attempts=3)
        async def async_flaky_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"Retry exhausted for {func.__name__} after {max_attempts} attempts",
                            extra={"function": func.__name__, "attempts": max_attempts, "error": str(e)}
                        )
                        raise

                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)
                    if jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__}, waiting {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(e)
                        }
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def timeout(seconds: float, default: Any = None):
    """
    Decorator to add timeout to synchronous functions.

    Usage:
        @timeout(5.0)
        def slow_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")

            # Only works on Unix
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, seconds)
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # Fallback for Windows - run without timeout protection
                return func(*args, **kwargs)

        return wrapper
    return decorator


async def async_timeout(coro, seconds: float, default: Any = None) -> Any:
    """
    Execute async coroutine with timeout.

    Usage:
        result = await async_timeout(my_coro(), 5.0, default="fallback")
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        if default is not None:
            logger.warning(f"Async operation timed out after {seconds}s, using default")
            return default
        raise


def fallback(fallback_func: Callable[..., T], exceptions: tuple = (Exception,)):
    """
    Decorator to provide fallback on failure.

    Usage:
        def get_default():
            return "default_value"

        @fallback(get_default)
        def risky_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.warning(
                    f"Function {func.__name__} failed, using fallback",
                    extra={"function": func.__name__, "error": str(e)}
                )
                return fallback_func(*args, **kwargs)

        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
neo4j_circuit = CircuitBreaker("neo4j", CircuitBreakerConfig(
    failure_threshold=5,
    timeout_seconds=30.0
))

ollama_circuit = CircuitBreaker("ollama", CircuitBreakerConfig(
    failure_threshold=3,
    timeout_seconds=60.0
))

kafka_circuit = CircuitBreaker("kafka", CircuitBreakerConfig(
    failure_threshold=5,
    timeout_seconds=30.0
))
