"""Structured JSON logging initialization using structlog."""

import logging
import sys
from typing import cast

import structlog


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """Configure structlog processors and standard library logging integration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "production":
        # Production: JSON logging for aggregation systems (Datadog, CloudWatch)
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: Colorful, human-readable key-value formatting
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Silence overly verbose third-party loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers.clear()
        mod_logger.propagate = True


configure_logging = setup_logging


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger instance for a given module name."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
