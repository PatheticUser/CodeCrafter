"""Animated spinner for CodeCrafter powered by Rich."""

import random
import threading
import time

from rich.status import Status

from config import (
    SPINNER_WORDS,
    SPINNER_WORD_SWITCH_INTERVAL,
)
from .display import console, Icons

class Spinner:
    """Thread-safe rich status animated spinner."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._status = None

    def start(self):
        self._stop_event.clear()
        self._status = Status(self._get_label(), console=console, spinner="dots")
        self._status.start()
        
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _get_label(self) -> str:
        word = random.choice(SPINNER_WORDS)
        return f"[dim]{word}[/]"

    def _spin(self):
        last_switch = time.time()
        try:
            while not self._stop_event.is_set():
                now = time.time()
                if now - last_switch >= SPINNER_WORD_SWITCH_INTERVAL:
                    if self._status:
                        self._status.update(self._get_label())
                    last_switch = now
                time.sleep(0.1)
        finally:
            if self._status:
                self._status.stop()
                self._status = None

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self._status:
            self._status.stop()
            self._status = None

# Global spinner instance
spinner = Spinner()
