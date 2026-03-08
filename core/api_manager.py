"""API Key management for Groq API with rotation support."""

import json
import os
import sys

from groq import Groq

from config import API_KEYS_FILE, BASE_DIR
from ui.display import c, Colors, Icons, show_error


def load_api_keys():
    """Load API keys from api_keys.json."""
    keys = []
    keys_file = os.path.join(BASE_DIR, API_KEYS_FILE)
    if os.path.exists(keys_file):
        try:
            with open(keys_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                keys = [
                    k.strip()
                    for k in loaded
                    if k.strip() and not k.startswith("gsk_your_")
                ]
        except Exception:
            pass
    return keys


class APIKeyManager:
    """Manages multiple API keys with silent automatic rotation on rate limits."""

    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.keys:
            print(f"  {c(Icons.ERROR, Colors.RED)}  No API keys found.")
            print(f"  {c(Icons.INFO, Colors.DIM)}  Add keys to {c('api_keys.json', Colors.CYAN)}")
            sys.exit(1)
        self.client = Groq(api_key=self.keys[self.current_index])

    def rotate(self):
        """Silently switch to the next API key. Returns True if rotated, False if all exhausted."""
        if len(self.keys) <= 1:
            return False
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.keys)
        if self.current_index == old_index:
            return False
        self.client = Groq(api_key=self.keys[self.current_index])
        return True

    def get_client(self):
        return self.client

    def key_count(self):
        return len(self.keys)
