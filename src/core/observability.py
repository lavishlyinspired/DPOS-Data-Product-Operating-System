"""
Observability Module
Provides APM metrics, distributed tracing, and monitoring capabilities.
"""
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from contextlib import contextmanager
from functools import wraps
import threading
import time
import logging
import uuid
import json

logger = logging.getLogger(__name__)


# Context variable for trace propagation
_trace_context = threading.local()


@dataclass
class Span:
    """Represents a single span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: list = field(default_factory=list)

    def finish(self, status: str = "ok"):
        """Finish the span."""
        self.end_time = time.time()
        self.status = status

    def set_tag(self, key: str, value: Any):
        """Set a tag on the span."""
        self.tags[key] = value

    def log(self, message: str, **kwargs):
        """Add a log entry to the span."""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **kwargs
        })

    @property
    def duration_ms(self) -> float:
        """Calculate span duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    def to_dict(self) -> Dict:
        """Convert span to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs
        }


class Tracer:
    """Distributed tracing implementation."""

    def __init__(self, service_name: str = "dpos-ecommerce"):
        self.service_name = service_name
        self._spans: list = []
        self._exporters: list = []

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None
    ) -> Span:
        """Start a new span."""
        trace_id = getattr(_trace_context, 'trace_id', None)
        parent_span_id = None

        if parent_span:
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        elif not trace_id:
            trace_id = uuid.uuid4().hex

        span = Span(
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=time.time()
        )

        _trace_context.trace_id = trace_id
        _trace_context.current_span = span

        return span

    def finish_span(self, span: Span, status: str = "ok"):
        """Finish and export a span."""
        span.finish(status)
        self._spans.append(span)
        self._export_span(span)

    def _export_span(self, span: Span):
        """Export span to configured exporters."""
        for exporter in self._exporters:
            try:
                exporter.export(span)
            except Exception as e:
                logger.warning(f"Failed to export span: {e}")

    def add_exporter(self, exporter):
        """Add a span exporter."""
        self._exporters.append(exporter)

    @contextmanager
    def trace(self, operation_name: str):
        """Context manager for tracing an operation."""
        span = self.start_span(operation_name)
        try:
            yield span
            self.finish_span(span, "ok")
        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.log(f"Error: {e}", level="error")
            self.finish_span(span, "error")
            raise

    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return getattr(_trace_context, 'current_span', None)

    def get_trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        return getattr(_trace_context, 'trace_id', None)


class ConsoleSpanExporter:
    """Exports spans to console for debugging."""

    def export(self, span: Span):
        """Export span to console."""
        logger.debug(f"TRACE: {json.dumps(span.to_dict(), default=str)}")


class MetricsCollector:
    """
    Collects and aggregates application metrics.
    Supports counters, gauges, histograms, and timers.
    """

    def __init__(self, service_name: str = "dpos-ecommerce"):
        self.service_name = service_name
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """Increment a counter metric."""
        key = self._make_key(name, tags)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Set a gauge metric."""
        key = self._make_key(name, tags)
        with self._lock:
            self._gauges[key] = value

    def histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a histogram value."""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            # Keep last 1000 values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    @contextmanager
    def timer(self, name: str, tags: Optional[Dict] = None):
        """Context manager to time an operation."""
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.histogram(f"{name}.duration_ms", duration_ms, tags)

    def _make_key(self, name: str, tags: Optional[Dict]) -> str:
        """Create a unique key for a metric."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            result = {
                "service": self.service_name,
                "timestamp": datetime.now(UTC).isoformat(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {}
            }

            for key, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    result["histograms"][key] = {
                        "count": len(values),
                        "min": sorted_values[0],
                        "max": sorted_values[-1],
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(sorted_values, 50),
                        "p95": self._percentile(sorted_values, 95),
                        "p99": self._percentile(sorted_values, 99)
                    }

            return result

    def _percentile(self, sorted_values: list, percentile: int) -> float:
        """Calculate a percentile from sorted values."""
        if not sorted_values:
            return 0
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        if f == c:
            return sorted_values[f]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# Global instances
_tracer: Optional[Tracer] = None
_metrics: Optional[MetricsCollector] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
        _tracer.add_exporter(ConsoleSpanExporter())
    return _tracer


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def traced(operation_name: Optional[str] = None):
    """Decorator to add tracing to a function."""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(op_name) as span:
                span.set_tag("function", func.__name__)
                span.set_tag("module", func.__module__)
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace(op_name) as span:
                span.set_tag("function", func.__name__)
                span.set_tag("module", func.__module__)
                return await func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def timed(metric_name: Optional[str] = None):
    """Decorator to add timing metrics to a function."""
    def decorator(func: Callable) -> Callable:
        name = metric_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            with metrics.timer(name):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                metrics.histogram(f"{name}.duration_ms", duration_ms)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def counted(metric_name: str, tags: Optional[Dict] = None):
    """Decorator to count function invocations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            metrics.increment(metric_name, tags=tags)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            metrics.increment(metric_name, tags=tags)
            return await func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# Health check support
class HealthChecker:
    """Centralized health checking for all dependencies."""

    def __init__(self):
        self._checks: Dict[str, Callable] = {}

    def register(self, name: str, check_func: Callable[[], bool]):
        """Register a health check function."""
        self._checks[name] = check_func

    def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": {}
        }

        for name, check_func in self._checks.items():
            try:
                is_healthy = check_func()
                results["checks"][name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "timestamp": datetime.now(UTC).isoformat()
                }
                if not is_healthy:
                    results["status"] = "unhealthy"
            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now(UTC).isoformat()
                }
                results["status"] = "unhealthy"

        return results


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
