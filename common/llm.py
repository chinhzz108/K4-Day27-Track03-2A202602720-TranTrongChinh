"""LLM factory. Returns an OpenAI-compatible chat model wired to OpenRouter."""

import os

from langchain_openai import ChatOpenAI


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not api_key:
        raise RuntimeError("LLM API key is not set — set GROQ_API_KEY or OPENROUTER_API_KEY in .env")

    base_url = os.environ.get("LLM_BASE_URL")
    if not base_url:
        if os.environ.get("GROQ_API_KEY") or (api_key and api_key.startswith("gsk_")):
            base_url = "https://api.groq.com/openai/v1"
        else:
            base_url = "https://openrouter.ai/api/v1"

    model = os.environ.get("LLM_MODEL")
    if not model:
        if "groq.com" in base_url or (api_key and api_key.startswith("gsk_")):
            model = "qwen/qwen3.8-27b"
        else:
            model = "openai/gpt-4o-mini"

    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


