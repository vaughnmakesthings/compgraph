import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():  # type: ignore[no-untyped-def]
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


async def generate_embedding(text: str) -> list[float]:
    def _encode() -> list[float]:
        model = _get_model()
        return model.encode(text, normalize_embeddings=True).tolist()  # type: ignore[no-any-return]

    return await asyncio.to_thread(_encode)


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    def _encode_batch() -> list[list[float]]:
        model = _get_model()
        return [v.tolist() for v in model.encode(texts, normalize_embeddings=True)]

    return await asyncio.to_thread(_encode_batch)
