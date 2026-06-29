"""
Centralized logging configuration for Mortgage RAG Pipeline.

Usage:
    from backend.logging_config import setup_logging, get_logger
    setup_logging()          # call once at startup
    logger = get_logger(__name__)

Log levels:
    DEBUG   — retrieval scores, chunk details, prompt sizes
    INFO    — request lifecycle, ingestion progress, LLM provider init
    WARNING — fallbacks, retries, degraded behavior
    ERROR   — failures, exceptions
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_configured = False


def setup_logging(log_level: str | None = None):
    """Configure root logger with console + file output."""
    global _configured
    if _configured:
        return
    _configured = True

    level_str = log_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_str.upper(), logging.INFO)

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"rag_{datetime.now().strftime('%Y%m%d')}.log"

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Console handler — INFO and above, concise format
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    # File handler — DEBUG and above, detailed format
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root.addHandler(console)
    root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("Logging initialized — level=%s, file=%s", level_str, log_file)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
