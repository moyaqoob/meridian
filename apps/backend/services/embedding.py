"""Batch + single embedding via NVIDIA nemotron-3-embed-1b (2048-dim)."""

from __future__ import annotations

from openai import AsyncOpenAI, OpenAI

from core.config import settings

_sync_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None


def _client() -> OpenAI:
    global _sync_client
    if _sync_client is None:
        _sync_client = OpenAI(
            api_key=settings.nvidia_api_key.get_secret_value(),
            base_url=settings.nvidia_api_base_url,
        )
    return _sync_client


def _async() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(
            api_key=settings.nvidia_api_key.get_secret_value(),
            base_url=settings.nvidia_api_base_url,
        )
    return _async_client


def _create_embeddings(
    client: OpenAI,
    texts: list[str],
    *,
    input_type: str,
) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        extra_body={"input_type": input_type},
    )
    return [item.embedding for item in response.data]


async def _create_embeddings_async(
    client: AsyncOpenAI,
    texts: list[str],
    *,
    input_type: str,
) -> list[list[float]]:
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        extra_body={"input_type": input_type},
    )
    return [item.embedding for item in response.data]


def embed_batch_sync(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed code chunks at ingest time. Use passage mode for indexing."""
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    client = _client()
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(
            _create_embeddings(client, batch, input_type="passage"),
        )
    return all_embeddings


async def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    if not texts:
        return []

    all_embeddings: list[list[float]] = []
    client = _async()
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(
            await _create_embeddings_async(client, batch, input_type="passage"),
        )
    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """Embed a PR diff (or enriched query) at review time. Use query mode."""
    vectors = await _create_embeddings_async(_async(), [text], input_type="query")
    return vectors[0]
