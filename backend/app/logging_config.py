"""
Structured logging configuration for JobApplicationTracker.

Provides JSON-formatted logs with optional CloudWatch integration.
Use: from .logging_config import setup_logging, get_logger
"""

import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Convert log records to structured JSON format."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_data["extra"] = record.extra_fields

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger(logging.Logger):
    """Custom logger with support for extra fields."""

    def info(self, msg, *args, extra_fields=None, **kwargs):
        """Log info with optional extra fields."""
        if extra_fields:
            extra = {"extra_fields": extra_fields}
        else:
            extra = {}
        super().info(msg, *args, extra=extra, **kwargs)

    def error(self, msg, *args, extra_fields=None, **kwargs):
        """Log error with optional extra fields."""
        if extra_fields:
            extra = {"extra_fields": extra_fields}
        else:
            extra = {}
        super().error(msg, *args, extra=extra, **kwargs)

    def warning(self, msg, *args, extra_fields=None, **kwargs):
        """Log warning with optional extra fields."""
        if extra_fields:
            extra = {"extra_fields": extra_fields}
        else:
            extra = {}
        super().warning(msg, *args, extra=extra, **kwargs)

    def debug(self, msg, *args, extra_fields=None, **kwargs):
        """Log debug with optional extra fields."""
        if extra_fields:
            extra = {"extra_fields": extra_fields}
        else:
            extra = {}
        super().debug(msg, *args, extra=extra, **kwargs)


def setup_logging(environment: Optional[str] = None) -> logging.Logger:
    """
    Initialize structured logging for the application.

    Args:
        environment: "development" or "production". Auto-detected from ENVIRONMENT env var.

    Returns:
        Configured root logger instance.
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # Use custom logger class
    logging.setLoggerClass(StructuredLogger)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

    # Remove any existing handlers (avoid duplicates)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (JSON format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = JsonFormatter()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # CloudWatch handler (production only)
    if environment == "production":
        try:
            import watchtower

            cw_handler = watchtower.CloudWatchLogHandler(
                log_group="/aws/lambda/JobApplicationTracker",
                stream_name=os.getenv("LAMBDA_FUNCTION_NAME", "auto-apply"),
                use_queues=False,  # Synchronous for Lambda
            )
            cw_handler.setLevel(logging.INFO)
            cw_handler.setFormatter(console_formatter)
            root_logger.addHandler(cw_handler)
            root_logger.info("CloudWatch handler initialized")
        except ImportError:
            root_logger.warning("watchtower not installed; CloudWatch logging disabled")
        except Exception as e:
            root_logger.error(f"Failed to initialize CloudWatch handler: {e}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.

    Usage:
        logger = get_logger(__name__)
        logger.info("Message", extra_fields={"user_id": 123})
    """
    return logging.getLogger(name)
