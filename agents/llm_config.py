"""Shared configuration for Artha's Groq-backed CrewAI agents."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import LLM


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GROQ_MODEL = "groq/qwen/qwen3.8-27b"

# Groq's free/on-demand tier allows only 1000 output tokens per minute for this
# model, so each call must request well under that. Override in .env if needed.
DEFAULT_MAX_TOKENS = 600


class GroqCompatibleLLM(LLM):
    """CrewAI LLM adapter that removes CrewAI-only message metadata.

    Recent CrewAI AgentExecutors add ``cache_breakpoint`` to prompt messages.
    That marker is meaningful to selected native providers, but Groq rejects
    it when CrewAI routes Groq models through LiteLLM.
    """

    def _format_messages_for_provider(self, messages):
        if isinstance(messages, str):
            return super()._format_messages_for_provider(messages)
        clean_messages = [
            {key: value for key, value in message.items() if key != "cache_breakpoint"}
            for message in messages
        ]
        return super()._format_messages_for_provider(clean_messages)


def get_groq_model() -> LLM:
    """Load project credentials and build the Groq-compatible CrewAI LLM."""
    env_file = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_file, override=False)
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        # An empty shell variable should not mask a populated project .env.
        load_dotenv(dotenv_path=env_file, override=True)
        api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Groq API key is missing. Add GROQ_API_KEY=your_key to the project .env file "
            "or set GROQ_API_KEY in your environment. Do not commit the key."
        )
    os.environ["GROQ_API_KEY"] = api_key
    model = os.getenv("ARTHA_LLM_MODEL", DEFAULT_GROQ_MODEL).strip()
    if not model.startswith("groq/"):
        raise RuntimeError("ARTHA_LLM_MODEL must use CrewAI's Groq format, for example groq/qwen/qwen3.8-27b.")

    max_tokens = int(os.getenv("ARTHA_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    kwargs = {"model": model, "temperature": 0.2, "max_tokens": max_tokens}

    # Optional: reduce hidden "thinking" tokens on reasoning models.
    # Set ARTHA_REASONING_EFFORT=none in .env only if Groq accepts it for your model.
    effort = os.getenv("ARTHA_REASONING_EFFORT", "").strip()
    if effort:
        kwargs["reasoning_effort"] = effort

    return GroqCompatibleLLM(**kwargs)