from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _clear_model_cache():
    from compgraph.enrichment.embeddings import _get_model

    _get_model.cache_clear()
    yield
    _get_model.cache_clear()


def _make_mock_model():
    model = MagicMock()
    fake_embedding = np.random.default_rng(42).random(384).astype(np.float32)
    fake_embedding = fake_embedding / np.linalg.norm(fake_embedding)
    model.encode.return_value = fake_embedding
    return model


@patch("compgraph.enrichment.embeddings._get_model")
async def test_generate_embedding_returns_384_dim(mock_get_model):
    mock_get_model.return_value = _make_mock_model()
    from compgraph.enrichment.embeddings import generate_embedding

    result = await generate_embedding("test text for embedding")

    assert isinstance(result, list)
    assert len(result) == 384


@patch("compgraph.enrichment.embeddings._get_model")
async def test_generate_embedding_returns_floats(mock_get_model):
    mock_get_model.return_value = _make_mock_model()
    from compgraph.enrichment.embeddings import generate_embedding

    result = await generate_embedding("another test")

    assert all(isinstance(v, float) for v in result)


@patch("compgraph.enrichment.embeddings._get_model")
async def test_generate_embedding_normalized(mock_get_model):
    mock_get_model.return_value = _make_mock_model()
    from compgraph.enrichment.embeddings import generate_embedding

    result = await generate_embedding("normalized check")
    norm = sum(v**2 for v in result) ** 0.5

    assert abs(norm - 1.0) < 0.01


@patch("compgraph.enrichment.embeddings._get_model")
async def test_generate_embedding_calls_model_with_normalize(mock_get_model):
    mock_model = _make_mock_model()
    mock_get_model.return_value = mock_model
    from compgraph.enrichment.embeddings import generate_embedding

    await generate_embedding("check normalize flag")

    mock_model.encode.assert_called_once_with("check normalize flag", normalize_embeddings=True)


@patch("compgraph.enrichment.embeddings._get_model")
async def test_generate_embeddings_batch(mock_get_model):
    mock_model = MagicMock()
    rng = np.random.default_rng(42)
    batch_result = rng.random((3, 384)).astype(np.float32)
    mock_model.encode.return_value = batch_result
    mock_get_model.return_value = mock_model
    from compgraph.enrichment.embeddings import generate_embeddings_batch

    texts = ["text one", "text two", "text three"]
    results = await generate_embeddings_batch(texts)

    assert len(results) == 3
    assert all(len(v) == 384 for v in results)
    assert all(isinstance(v, list) for v in results)


@patch("sentence_transformers.SentenceTransformer")
async def test_model_is_loaded_only_once(mock_sentence_transformer):
    """Verify that the model is a singleton loaded only once via lru_cache."""
    mock_model = _make_mock_model()
    mock_sentence_transformer.return_value = mock_model
    from compgraph.enrichment.embeddings import generate_embedding

    await generate_embedding("first call")
    await generate_embedding("second call")

    mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")
    assert mock_model.encode.call_count == 2
