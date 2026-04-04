"""Structured logging for CodeCrafter.

Provides a project-wide logger with colored console output and optional
file logging. Usage:

    from services.logger import logger
    logger.info("Agent started")
    logger.warning("Model rate-limited", model="qwen3.5")
    logger.error("Session save failed", exc_info=True)
"""

import logging
import os
import sys
from datetime import datetime


class _ColorFormatter(logging.Formatter):
    """Terminal-friendly colored log formatter."""

    COLORS = {
        logging.DEBUG: "\033[2m",       # dim
        logging.INFO: "\033[36m",       # cyan
        logging.WARNING: "\033[33m",    # yellow
        logging.ERROR: "\033[31m",      # red
        logging.CRITICAL: "\033[1;31m", # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        levelname = record.levelname.lower()
        msg = record.getMessage()
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        formatted = f"  {color}[{ts}] {levelname}: {msg}{self.RESET}"
        if record.exc_info and record.exc_info[1]:
            formatted += f"\n  {color}{self._formatException(record.exc_info)}{self.RESET}"
        return formatted


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure the project-wide logger.

    Args:
        verbose: If True, console output is DEBUG; otherwise WARNING
                 (so normal runs stay clean).
        log_file: Optional path to a file for full DEBUG logs.
    """
    root = logging.getLogger("codecrafter")
    root.setLevel(logging.DEBUG)

    # Remove any existing handlers (re-entrant safe)
    root.handlers.clear()

    # Console handler — quiet unless verbose
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(_ColorFormatter())
    root.addHandler(console)

    # Optional file handler — always DEBUG
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(fh)


# Module-level convenience logger
logger = logging.getLogger("codecrafter")
