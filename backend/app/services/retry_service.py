"""
Retry logic with exponential backoff for automatic failure recovery.

Provides intelligent retry strategies for transient vs. permanent errors.
"""

import asyncio
import logging
from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Any, Tuple

logger = logging.getLogger(__name__)

def _safe_log(log_func, message: str, extra_fields: dict = None):
    """Safely call log function, handling both StructuredLogger and standard Logger."""
    try:
        if extra_fields:
            log_func(message, extra_fields=extra_fields)
        else:
            log_func(message)
    except TypeError:
        # Fallback for standard logger (doesn't support extra_fields)
        if extra_fields:
            message_with_context = f"{message} | {extra_fields}"
        log_func(message)


class RetryStrategy(Enum):
    """Retry strategies available."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    IMMEDIATE = "immediate"


async def should_retry(
    error: Exception,
    attempt: int,
    max_attempts: int = 3,
) -> Tuple[bool, int]:
    """
    Determine if we should retry and how long to wait.

    Args:
        error: The exception that occurred
        attempt: Current attempt number (0-indexed)
        max_attempts: Maximum number of attempts (default 3)

    Returns:
        Tuple of (should_retry: bool, wait_seconds: int)
    """
    # Don't retry if max attempts reached
    if attempt >= max_attempts:
        return False, 0

    error_str = str(error).lower()

    # Don't retry validation/auth errors (permanent)
    if isinstance(error, ValueError):
        return False, 0

    if isinstance(error, (TypeError, AttributeError)):
        return False, 0

    if "validation" in error_str or "required" in error_str:
        return False, 0

    # Retry network/timeout errors (transient)
    if isinstance(error, (asyncio.TimeoutError, ConnectionError, TimeoutError)):
        wait_seconds = 2 ** attempt  # Exponential: 1s, 2s, 4s, 8s
        return True, wait_seconds

    # Retry form detection failures (sometimes transient due to JS rendering)
    if "form" in error_str or "field" in error_str or "selector" in error_str:
        wait_seconds = 2 ** attempt
        return True, wait_seconds

    # Retry browser/playwright errors (usually transient)
    if "browser" in error_str or "playwright" in error_str or "navigation" in error_str:
        wait_seconds = 2 ** attempt
        return True, wait_seconds

    # Default: don't retry unknown errors
    return False, 0


async def execute_with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    on_retry_callback: Optional[Callable] = None,
    context_fields: Optional[dict] = None,
    **kwargs
) -> Any:
    """
    Execute an async function with automatic retry on failure.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_attempts: Maximum attempts (default 3)
        on_retry_callback: Async callback called on each retry
        context_fields: Extra fields for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result of func if successful

    Raises:
        Last exception if all retries fail

    Example:
        result = await execute_with_retry(
            my_async_function,
            job_id,
            profile,
            max_attempts=3,
            on_retry_callback=log_retry,
            context_fields={"app_id": 123}
        )
    """
    if context_fields is None:
        context_fields = {}

    attempt = 0
    last_error = None

    while attempt < max_attempts:
        try:
            result = await func(*args, **kwargs)

            if attempt > 0:
                pass  # Successfully recovered from previous failure

            return result

        except Exception as e:
            attempt += 1
            last_error = e

            should_retry_result, wait_time = await should_retry(e, attempt - 1, max_attempts)

            if not should_retry_result:
                raise

            # Call retry callback if provided
            if on_retry_callback:
                try:
                    if asyncio.iscoroutinefunction(on_retry_callback):
                        await on_retry_callback(attempt, wait_time, e)
                    else:
                        on_retry_callback(attempt, wait_time, e)
                except Exception:
                    pass  # Ignore callback errors

            await asyncio.sleep(wait_time)

    # All attempts exhausted
    raise last_error


class RetryableOperation:
    """Context manager for retry logic with automatic error tracking."""

    def __init__(
        self,
        operation_name: str,
        max_attempts: int = 3,
        context_fields: Optional[dict] = None,
    ):
        """
        Initialize retry context.

        Args:
            operation_name: Name of operation (for logging)
            max_attempts: Max retry attempts
            context_fields: Extra fields for logging
        """
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.context_fields = context_fields or {}
        self.attempt = 0
        self.errors = []

    async def __aenter__(self):
        """Enter async context."""
        self.attempt += 1
        logger.debug(
            f"Starting {self.operation_name} (attempt {self.attempt}/{self.max_attempts})",
            extra_fields={**self.context_fields, "attempt": self.attempt}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if exc_type is None:
            if self.attempt > 1:
                logger.info(
                    f"{self.operation_name} succeeded after retry",
                    extra_fields={
                        **self.context_fields,
                        "successful_attempt": self.attempt,
                        "previous_errors": len(self.errors),
                    }
                )
            return False  # Don't suppress exception

        # Exception occurred
        should_retry_flag, wait_time = await should_retry(exc_val, self.attempt - 1, self.max_attempts)
        self.errors.append({
            "attempt": self.attempt,
            "error": str(exc_val)[:200],
            "error_type": type(exc_val).__name__,
        })

        if not should_retry_flag or self.attempt >= self.max_attempts:
            logger.error(
                f"{self.operation_name} failed permanently",
                extra_fields={
                    **self.context_fields,
                    "attempt": self.attempt,
                    "max_attempts": self.max_attempts,
                    "error_history": self.errors,
                }
            )
            return False  # Re-raise exception

        logger.warning(
            f"{self.operation_name} failed, will retry",
            extra_fields={
                **self.context_fields,
                "attempt": self.attempt,
                "wait_seconds": wait_time,
                "error": str(exc_val)[:100],
            }
        )

        await asyncio.sleep(wait_time)
        return True  # Suppress exception, allow retry at call site


def calculate_next_retry_time(attempt: int, strategy: RetryStrategy = RetryStrategy.EXPONENTIAL) -> datetime:
    """
    Calculate when the next retry should happen.

    Args:
        attempt: Current attempt number (0-indexed)
        strategy: Retry strategy

    Returns:
        UTC datetime when next retry should occur
    """
    if strategy == RetryStrategy.EXPONENTIAL:
        wait_seconds = 2 ** attempt  # 1, 2, 4, 8, 16, ...
    elif strategy == RetryStrategy.LINEAR:
        wait_seconds = attempt * 30  # 0, 30, 60, 90, ...
    else:  # IMMEDIATE
        wait_seconds = 0

    return datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)
