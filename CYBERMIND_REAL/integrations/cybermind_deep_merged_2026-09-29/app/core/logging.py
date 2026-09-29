from __future__ import annotations

import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"


def _build() -> logging.Logger:
    logger = logging.getLogger("cybermind.app")
    if not logger.handlers:
        level = os.getenv("CYBERMIND_LOG_LEVEL", "INFO").upper()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level, logging.INFO))
        logger.propagate = False
    return logger


log = _build()


def redact(value: str | None) -> str:
    """Redact obvious secrets from log output."""
    if not value:
        return ""
    v = str(value)
    if len(v) <= 4:
        return "***"
    return v[:2] + "***" + v[-2:]
