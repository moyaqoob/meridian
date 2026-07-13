"""Batch + single embedding via OpenAI text-embedding-3-small."""

from __future__ import annotations

from openai import AsyncOpenAI, OpenAI

from core.config import settings

_sync_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None


def _client() -> OpenAI:
    global _sync_client
    if _sync_client is None:
        _sync_client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    return _sync_client


def _async() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    return _async_client


def embed_batch_sync(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    client = _client()
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)
    return all_embeddings


async def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    client = _async()
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)
    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """Embed a PR diff (or enriched query) at review time."""
    response = await _async().embeddings.create(
        model="text-embedding-3-small",
        input=[text],
    )
    return response.data[0].embedding
