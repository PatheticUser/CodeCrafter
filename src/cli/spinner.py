"""Animated spinner for CodeCrafter."""

import random
import threading
import time
import sys

from src.core.settings import settings
from src.cli.display import c, Colors, dim


class Spinner:
    """Animated terminal spinner with NerdFont circle animation."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._frame_index = 0

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        word = random.choice(settings.SPINNER_WORDS)
        last_switch = time.time()
        try:
            while not self._stop_event.is_set():
                now = time.time()
                if now - last_switch >= settings.SPINNER_WORD_SWITCH_INTERVAL:
                    word = random.choice(settings.SPINNER_WORDS)
                    last_switch = now
                frame = settings.SPINNER_FRAMES[self._frame_index % len(settings.SPINNER_FRAMES)]
                self._frame_index += 1
                line = f"\r  {c(frame, Colors.CYAN)}  {dim(word)}"
                sys.stdout.write(line)
                sys.stdout.flush()
                time.sleep(settings.SPINNER_FRAME_DURATION)
        finally:
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)


spinner = Spinner()
