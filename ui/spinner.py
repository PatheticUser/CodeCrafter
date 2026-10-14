"""Animated thinking spinner for CodeCrafter — rich Live powered.

Renders a single in-place status line (frame + rotating word) while the
agent blocks on a model call, and clears it when stopped.
"""

import random
import time

from rich.live import Live
from rich.text import Text

from config import (
    SPINNER_FRAME_DURATION,
    SPINNER_FRAMES,
    SPINNER_WORD_SWITCH_INTERVAL,
    SPINNER_WORDS,
)

from .display import console


class _ThinkingView:
    """Renderable that animates a spinner frame + a rotating status word."""

    def __init__(self, message: str = ""):
        self._custom = message
        self._start = time.monotonic()
        # Random offset so the rotating word doesn't start at the same place each time
        self._word_offset = random.random() * SPINNER_WORD_SWITCH_INTERVAL

    def __rich__(self) -> Text:
        elapsed = time.monotonic() - self._start
        frame = SPINNER_FRAMES[int(elapsed / SPINNER_FRAME_DURATION) % len(SPINNER_FRAMES)]
        word = SPINNER_WORDS[
            int((elapsed + self._word_offset) / SPINNER_WORD_SWITCH_INTERVAL) % len(SPINNER_WORDS)
        ]
        message = (self._custom or word).strip()
        t = Text()
        t.append("  ")
        t.append(f"{frame} ", style="bold cyan")
        t.append(message, style="dim")
        return t


class Spinner:
    """Single-line animated status indicator (start/stop API)."""

    def __init__(self):
        self._live: Live | None = None

    def start(self, message: str = ""):
        self.stop()  # never leave a previous line behind
        self._live = Live(
            _ThinkingView(message),
            console=console,
            transient=True,  # remove the line on stop
            refresh_per_second=max(1, int(1 / SPINNER_FRAME_DURATION)),
        )
        self._live.start()

    def stop(self):
        if self._live is not None:
            if self._live.is_started:
                self._live.stop()
            self._live = None


# Global spinner instance
spinner = Spinner()
