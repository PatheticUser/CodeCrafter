"""API client and model fallback management for Ollama Cloud."""

import sys

from openai import OpenAI

from src.core.settings import settings
from src.cli.display import c, Colors, Icons


class OllamaClient:
    """Manages the Ollama API client with automatic model fallback.

    When the active model fails (rate limit, unavailable, etc.), calling
    ``fallback()`` switches to the next model in the fallback chain.
    """

    def __init__(self, primary_model=None):
        """Initialize with a primary model. Falls back through FALLBACK_MODELS on errors.

        Args:
            primary_model: The model to start with. If it's in FALLBACK_MODELS,
                          the chain starts from that position. Otherwise it's
                          tried first, then the chain is used.
        """
        self.client = None

        fallback_models = settings.FALLBACK_MODELS

        # Build the model chain with the primary model first
        if primary_model and primary_model in fallback_models:
            idx = fallback_models.index(primary_model)
            self.models = fallback_models[idx:] + fallback_models[:idx]
        elif primary_model:
            self.models = [primary_model] + list(fallback_models)
        else:
            self.models = list(fallback_models)

        self.current_index = 0
        self._init_client()

    def _init_client(self):
        """Initialize the OpenAI client pointing to Ollama."""
        try:
            self.client = OpenAI(
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama",
            )
        except Exception as e:
            print(f"  {c(Icons.ERROR, Colors.RED)}  Failed to connect to Ollama: {e}")
            print(f"  {c(Icons.INFO, Colors.DIM)}  Make sure Ollama is running: {c('ollama serve', Colors.CYAN)}")
            sys.exit(1)

    @property
    def active_model(self):
        """Return the currently active model name."""
        return self.models[self.current_index]

    def fallback(self):
        """Switch to the next model in the fallback chain.

        Returns:
            The new model name if switched, or None if all models exhausted.
        """
        if self.current_index + 1 < len(self.models):
            self.current_index += 1
            return self.models[self.current_index]
        return None

    def reset(self):
        """Reset back to the primary model (for the next user turn)."""
        self.current_index = 0

    def model_count(self):
        """Return total number of models in the fallback chain."""
        return len(self.models)

    def get_client(self):
        """Return the OpenAI-compatible client."""
        return self.client
