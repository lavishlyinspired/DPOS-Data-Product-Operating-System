"""
DPOS Structured Logging Module
JSON structured logging with correlation IDs and context propagation.
"""
import logging
import json
import sys
import uuid
from datetime import datetime, UTC
from typing import Optional, Any, Dict
from contextvars import ContextVar
from functools import wraps
import traceback

from src.core.config import settings


# Context variables for request tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
agent_name_var: ContextVar[Optional[str]] = ContextVar('agent_name', default=None)


def get_correlation_id() -> str:
    """Get or generate correlation ID."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(cid)


def set_request_context(
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> None:
    """Set request context for logging."""
    if correlation_id:
        correlation_id_var.set(correlation_id)
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def set_agent_context(agent_name: str) -> None:
    """Set agent context for logging."""
    agent_name_var.set(agent_name)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context variables
        cid = correlation_id_var.get()
        if cid:
            log_data["correlation_id"] = cid

        rid = request_id_var.get()
        if rid:
            log_data["request_id"] = rid

        uid = user_id_var.get()
        if uid:
            log_data["user_id"] = uid

        agent = agent_name_var.get()
        if agent:
            log_data["agent"] = agent

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Structured logger wrapper with context and extra data support.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._configure()

    def _configure(self):
        """Configure the logger with JSON handler."""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, settings.log_level))
            self.logger.propagate = False

    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal log method with extra data support."""
        record_extra = {}
        if extra:
            record_extra['extra_data'] = extra

        self.logger.log(level, message, extra=record_extra, **kwargs)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, extra, **kwargs)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, extra, **kwargs)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, extra, **kwargs)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, extra, exc_info=exc_info, **kwargs)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info, **kwargs)

    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log exception with traceback."""
        self._log(logging.ERROR, message, extra, exc_info=True, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def log_function_call(logger: Optional[StructuredLogger] = None):
    """
    Decorator to log function calls with timing.

    Usage:
        @log_function_call()
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            func_name = func.__qualname__

            _logger.debug(
                f"Calling {func_name}",
                extra={"function": func_name, "args_count": len(args), "kwargs_keys": list(kwargs.keys())}
            )

            start_time = datetime.now(UTC)
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now(UTC) - start_time).total_seconds()

                _logger.debug(
                    f"Completed {func_name}",
                    extra={"function": func_name, "duration_seconds": duration, "success": True}
                )
                return result

            except Exception as e:
                duration = (datetime.now(UTC) - start_time).total_seconds()
                _logger.error(
                    f"Failed {func_name}: {str(e)}",
                    extra={"function": func_name, "duration_seconds": duration, "success": False, "error": str(e)},
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


def log_async_function_call(logger: Optional[StructuredLogger] = None):
    """
    Decorator to log async function calls with timing.

    Usage:
        @log_async_function_call()
        async def my_async_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            func_name = func.__qualname__

            _logger.debug(
                f"Calling {func_name}",
                extra={"function": func_name, "args_count": len(args), "kwargs_keys": list(kwargs.keys())}
            )

            start_time = datetime.now(UTC)
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now(UTC) - start_time).total_seconds()

                _logger.debug(
                    f"Completed {func_name}",
                    extra={"function": func_name, "duration_seconds": duration, "success": True}
                )
                return result

            except Exception as e:
                duration = (datetime.now(UTC) - start_time).total_seconds()
                _logger.error(
                    f"Failed {func_name}: {str(e)}",
                    extra={"function": func_name, "duration_seconds": duration, "success": False, "error": str(e)},
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


# Default application logger
app_logger = get_logger("dpos")
