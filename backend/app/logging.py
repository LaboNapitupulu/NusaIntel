from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper(), force=True)
    # HTTPX request lines include the full query string. BPS credentials are query
    # parameters, so transport loggers must never emit request URLs at INFO/DEBUG.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
