"""Tests for content-based enrichment deduplication."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from compgraph.enrichment.fingerprint import compute_content_hash
from compgraph.enrichment.schemas import EntityMention, Pass1Result, Pass2Result

# ---------------------------------------------------------------------------
# compute_content_hash tests
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    """Tests for the compute_content_hash utility function."""

    def test_same_content_same_hash(self):
        """Identical title+body should produce identical hashes."""
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit Best Buy stores weekly.")
        h2 = compute_content_hash("Samsung Brand Ambassador", "Visit Best Buy stores weekly.")
        assert h1 == h2

    def test_different_titles_different_hash(self):
        """Different titles should produce different hashes."""
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit stores weekly.")
        h2 = compute_content_hash("Samsung Merchandiser", "Visit stores weekly.")
        assert h1 != h2

    def test_different_body_different_hash(self):
        """Different body text should produce different hashes."""
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit Best Buy stores weekly.")
        h2 = compute_content_hash("Samsung Brand Ambassador", "Visit Target stores weekly.")
        assert h1 != h2

    def test_location_not_in_hash(self):
        """Location is not part of the hash — the function signature excludes it by design."""
        import inspect

        # The hash function deliberately only takes (title, full_text),
        # so location cannot influence the hash.
        sig = inspect.signature(compute_content_hash)
        assert list(sig.parameters.keys()) == ["title", "full_text"]

        # Same title+body from different cities produces the same hash
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit stores weekly.")
        h2 = compute_content_hash("Samsung Brand Ambassador", "Visit stores weekly.")
        assert h1 == h2

    def test_whitespace_normalization(self):
        """Extra whitespace in title or body should be normalized."""
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit stores weekly.")
        h2 = compute_content_hash("Samsung  Brand  Ambassador", "Visit  stores  weekly.")
        assert h1 == h2

    def test_case_normalization(self):
        """Case differences should be normalized."""
        h1 = compute_content_hash("Samsung Brand Ambassador", "Visit stores weekly.")
        h2 = compute_content_hash("SAMSUNG BRAND AMBASSADOR", "VISIT STORES WEEKLY.")
        assert h1 == h2

    def test_empty_body(self):
        """Empty body should still produce a valid hash."""
        h = compute_content_hash("Samsung Brand Ambassador", "")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_empty_title(self):
        """Empty title should still produce a valid hash."""
        h = compute_content_hash("", "Visit stores weekly.")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_both_empty(self):
        """Both empty should produce a valid hash."""
        h = compute_content_hash("", "")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_city_in_body_produces_different_hash(self):
        """If the ATS embeds the city name in the body, hashes will differ (correct behavior)."""
        h1 = compute_content_hash(
            "Samsung Brand Ambassador",
            "Visit Best Buy stores in Dallas, TX weekly.",
        )
        h2 = compute_content_hash(
            "Samsung Brand Ambassador",
            "Visit Best Buy stores in Houston, TX weekly.",
        )
        assert h1 != h2

    def test_deterministic(self):
        """Same inputs always produce the same output."""
        for _ in range(10):
            h = compute_content_hash("Test Title", "Test body text.")
            assert h == compute_content_hash("Test Title", "Test body text.")

    def test_hash_is_hex_sha256(self):
        """Hash should be a 64-character lowercase hex string (SHA-256)."""
        h = compute_content_hash("Title", "Body")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_role_prefixes_not_stripped(self):
        """Different role prefixes should produce different hashes.

        Unlike fingerprinting, the content hash preserves role prefixes
        because a Field Rep and a Merchandiser are distinct roles even
        with the same body text.
        """
        h1 = compute_content_hash("Field Rep: Samsung", "Visit stores.")
        h2 = compute_content_hash("Merchandiser: Samsung", "Visit stores.")
        assert h1 != h2

    def test_delimiter_collision_resistant(self):
        """Pipe characters in content should not cause hash collisions.

        Uses null-byte separator internally so 'A|B' + 'C' differs
        from 'A' + 'B|C'.
        """
        h1 = compute_content_hash("Software|Engineer", "Remote")
        h2 = compute_content_hash("Software", "Engineer|Remote")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Pass 1 dedup orchestrator tests
# ---------------------------------------------------------------------------


def _make_posting(
    posting_id=None,
    title="Samsung Brand Ambassador",
    location="Dallas, TX",
    full_text="Visit Best Buy stores weekly.",
):
    """Create a mock (Posting, PostingSnapshot) tuple."""
    posting = MagicMock()
    posting.id = posting_id or uuid.uuid4()
    posting.company_id = uuid.uuid4()

    snapshot = MagicMock()
    snapshot.id = uuid.uuid4()
    snapshot.title_raw = title
    snapshot.location_raw = location
    snapshot.full_text_raw = full_text

    return posting, snapshot


def _make_pass1_result(**overrides):
    """Create a Pass1Result with default field rep values."""
    defaults = {
        "role_archetype": "field_rep",
        "role_level": "entry",
        "employment_type": "full_time",
        "travel_required": True,
        "pay_type": "hourly",
        "pay_min": 20.0,
        "pay_max": 25.0,
        "pay_frequency": "hour",
        "has_commission": True,
        "has_benefits": True,
        "content_role_specific": "Visit 10-15 Best Buy stores weekly.",
        "content_boilerplate": "We are an equal opportunity employer.",
        "content_qualifications": "Must have reliable transportation.",
        "content_responsibilities": "Travel to retail stores.",
        "tools_mentioned": ["Salesforce"],
        "kpis_mentioned": ["sales targets"],
        "store_count": 15,
    }
    defaults.update(overrides)
    return Pass1Result(**defaults)


def _wrap_llm(result, input_tokens=100, output_tokens=50):
    """Wrap a parsed result in LLMCallResult for orchestrator mocks."""
    from compgraph.enrichment.retry import LLMCallResult

    return LLMCallResult(result=result, input_tokens=input_tokens, output_tokens=output_tokens)


def _make_pass2_result(entities=None):
    """Create a Pass2Result."""
    if entities is None:
        entities = [
            EntityMention(entity_name="Samsung", entity_type="client_brand", confidence=0.95),
            EntityMention(entity_name="Best Buy", entity_type="retailer", confidence=0.90),
        ]
    return Pass2Result(entities=entities)


class TestPass1Dedup:
    """Test that Pass 1 deduplication correctly reduces API calls."""

    @pytest.mark.asyncio
    async def test_identical_postings_single_api_call(self):
        """Three postings with identical title+body should result in only 1 API call."""
        # Three postings: same title+body, different locations
        postings = [
            _make_posting(title="Samsung BA", location="Dallas, TX", full_text="Visit stores."),
            _make_posting(title="Samsung BA", location="Houston, TX", full_text="Visit stores."),
            _make_posting(title="Samsung BA", location="Austin, TX", full_text="Visit stores."),
        ]

        pass1_result = _make_pass1_result()
        mock_enrich = AsyncMock(return_value=_wrap_llm(pass1_result))
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # Only 1 API call for 3 postings
        assert mock_enrich.call_count == 1
        # All 3 postings got enrichments saved
        assert mock_save.call_count == 3
        assert result.succeeded == 3
        assert result.failed == 0
        # Dedup savings tracked
        assert result.skipped == 2

    @pytest.mark.asyncio
    async def test_unique_postings_individual_api_calls(self):
        """Postings with different content should each get their own API call."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit Best Buy stores."),
            _make_posting(title="Sony Merchandiser", full_text="Stock shelves at Target."),
            _make_posting(title="LG Brand Rep", full_text="Demo products at Costco."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # 3 unique postings = 3 API calls
        assert mock_enrich.call_count == 3
        assert mock_save.call_count == 3
        assert result.succeeded == 3
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_mixed_unique_and_duplicate(self):
        """Mix of unique and duplicate postings should deduplicate correctly."""
        postings = [
            # Group 1: two duplicates
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            # Group 2: unique
            _make_posting(title="Sony Merchandiser", full_text="Stock shelves."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # 2 groups = 2 API calls
        assert mock_enrich.call_count == 2
        # All 3 postings saved
        assert mock_save.call_count == 3
        assert result.succeeded == 3
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_leader_failure_fallback(self):
        """When leader fails, followers are processed individually (leader not retried)."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
        ]

        call_count = 0

        async def _failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API error")
            return _wrap_llm(_make_pass1_result())

        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch(
                "compgraph.enrichment.orchestrator.enrich_posting_pass1",
                side_effect=_failing_then_succeeding,
            ),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # Leader failed (1 call), 1 follower processed individually (1 call)
        # Leader is NOT retried — avoids wasting API call on likely persistent error
        assert call_count == 2  # 1 leader fail + 1 follower
        assert result.succeeded == 1  # follower succeeded
        assert result.failed == 1  # leader failed
        # No dedup savings when fallback fires
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_fallback_cache_reuse_skips_api(self):
        """After first follower succeeds in fallback, remaining followers reuse cache (no API)."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
        ]

        call_count = 0

        async def _failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API error")
            return _wrap_llm(_make_pass1_result())

        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch(
                "compgraph.enrichment.orchestrator.enrich_posting_pass1",
                side_effect=_failing_then_succeeding,
            ),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # Leader failed (1 call), first follower succeeds via API (1 call),
        # remaining 2 followers reuse cache — only 2 API calls total
        assert call_count == 2
        # 3 followers succeeded (1 via API + 2 via cache), leader failed
        assert result.succeeded == 3
        assert result.failed == 1
        # 3 saves for followers (all 3 succeed)
        assert mock_save.call_count == 3

    @pytest.mark.asyncio
    async def test_single_posting_no_overhead(self):
        """A single posting should work normally with no grouping overhead."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit stores."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        assert mock_enrich.call_count == 1
        assert mock_save.call_count == 1
        assert result.succeeded == 1
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_empty_batch_no_processing(self):
        """Empty batch should return zero results."""
        mock_fetch = AsyncMock(return_value=[])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_aborts_remaining_groups(self):
        """Circuit breaker should stop processing after consecutive API failures."""
        from compgraph.enrichment.retry import EnrichmentAPIError, ErrorCategory

        # 4 groups (unique content) — breaker threshold=2 should stop after 2 failures
        postings = [
            _make_posting(title="Job A", full_text="Content A"),
            _make_posting(title="Job B", full_text="Content B"),
            _make_posting(title="Job C", full_text="Content C"),
            _make_posting(title="Job D", full_text="Content D"),
        ]

        mock_enrich = AsyncMock(
            side_effect=EnrichmentAPIError("Rate limited", ErrorCategory.RATE_LIMIT)
        )
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.settings") as mock_settings,
        ):
            mock_settings.ENRICHMENT_CIRCUIT_BREAKER_THRESHOLD = 2

            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=1)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # Breaker trips after 2 failures — remaining groups should NOT be attempted
        # With concurrency=1, groups process sequentially, so at most 2 API calls
        assert mock_enrich.call_count <= 3  # at most threshold calls before break
        assert mock_save.call_count == 0  # no successes
        assert result.failed > 0
        assert result.succeeded == 0


# ---------------------------------------------------------------------------
# Pass 2 dedup orchestrator tests
# ---------------------------------------------------------------------------


def _make_pass2_posting(
    posting_id=None,
    title="Samsung Brand Ambassador",
    location="Dallas, TX",
    full_text="Visit Best Buy stores weekly.",
    content_role_specific="Visit 10-15 Best Buy stores weekly.",
):
    """Create a mock (Posting, PostingSnapshot, PostingEnrichment) tuple for Pass 2."""
    posting = MagicMock()
    posting.id = posting_id or uuid.uuid4()
    posting.company_id = uuid.uuid4()

    snapshot = MagicMock()
    snapshot.id = uuid.uuid4()
    snapshot.title_raw = title
    snapshot.location_raw = location
    snapshot.full_text_raw = full_text

    enrichment = MagicMock()
    enrichment.id = uuid.uuid4()
    enrichment.content_role_specific = content_role_specific

    return posting, snapshot, enrichment


class TestPass2Dedup:
    """Test that Pass 2 deduplication correctly reduces API calls."""

    @pytest.mark.asyncio
    async def test_identical_postings_single_api_call(self):
        """Three postings with identical content should result in only 1 API call."""
        postings = [
            _make_pass2_posting(
                title="Samsung BA",
                location="Dallas, TX",
                content_role_specific="Visit Best Buy stores.",
            ),
            _make_pass2_posting(
                title="Samsung BA",
                location="Houston, TX",
                content_role_specific="Visit Best Buy stores.",
            ),
            _make_pass2_posting(
                title="Samsung BA",
                location="Austin, TX",
                content_role_specific="Visit Best Buy stores.",
            ),
        ]

        pass2_result = _make_pass2_result()
        mock_enrich = AsyncMock(return_value=_wrap_llm(pass2_result))
        mock_resolve = AsyncMock(return_value=MagicMock(brand_id=uuid.uuid4()))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_enrich),
            patch("compgraph.enrichment.orchestrator.resolve_entity", mock_resolve),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            # Need pass1 to be set for finish_pass2 to work
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 3
            result = await orch.run_pass2(run)

        # Only 1 API call for 3 postings
        assert mock_enrich.call_count == 1
        # All 3 postings get brand mentions saved
        assert mock_save_mentions.call_count == 3
        # All 3 marked as Pass 2 complete
        assert mock_mark_p2.call_count == 3
        assert result.succeeded == 3
        assert result.skipped == 2

    @pytest.mark.asyncio
    async def test_pass2_no_entities_still_marks_complete(self):
        """Postings with no entities should still be marked as Pass 2 complete."""
        postings = [
            _make_pass2_posting(
                title="Generic Job",
                content_role_specific="No brand mentions here.",
            ),
        ]

        empty_result = Pass2Result(entities=[])
        mock_enrich = AsyncMock(return_value=_wrap_llm(empty_result))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_enrich),
            patch("compgraph.enrichment.orchestrator.resolve_entity"),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 1
            result = await orch.run_pass2(run)

        # No entities → no brand mentions saved
        assert mock_save_mentions.call_count == 0
        # Still marked as Pass 2 complete
        assert mock_mark_p2.call_count == 1
        assert result.succeeded == 1


# ---------------------------------------------------------------------------
# Cache isolation tests
# ---------------------------------------------------------------------------


class TestCacheIsolation:
    """Verify that the content cache is properly scoped to each run."""

    @pytest.mark.asyncio
    async def test_cache_does_not_persist_across_runs(self):
        """Each run on the SAME orchestrator should start with a fresh cache."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit stores."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch(
                "compgraph.enrichment.orchestrator.fetch_unenriched_postings",
                # Each run fetches once (1 < batch_size=10 triggers break)
                AsyncMock(side_effect=[postings, postings]),
            ),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            # Reuse the SAME orchestrator instance for both runs
            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)

            # Run 1
            run1 = EnrichmentRun()
            await orch.run_pass1(run1)
            assert mock_enrich.call_count == 1

            # Run 2 on the same orchestrator — should NOT reuse run 1's cache
            run2 = EnrichmentRun()
            await orch.run_pass1(run2)
            assert mock_enrich.call_count == 2  # Fresh call, not cached


class TestCrossBatchCache:
    """Verify that cache persists across batches within a single run."""

    @pytest.mark.asyncio
    async def test_cache_persists_across_batches_in_same_run(self):
        """Content cached in batch 1 should produce cache hit in batch 2."""
        # Batch 1: posting A with unique content
        batch1 = [
            _make_posting(title="Samsung BA", location="Dallas, TX", full_text="Visit stores."),
        ]
        # Batch 2: posting B with the SAME content (different location)
        batch2 = [
            _make_posting(title="Samsung BA", location="Houston, TX", full_text="Visit stores."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()
        # Return batch1, then batch2, then empty to stop
        mock_fetch = AsyncMock(side_effect=[batch1, batch2, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            # Use batch_size=1 so each posting is a separate batch
            orch = EnrichmentOrchestrator(batch_size=1, concurrency=5)
            run = EnrichmentRun()
            result = await orch.run_pass1(run)

        # Only 1 API call: batch 1 calls LLM, batch 2 gets cache hit
        assert mock_enrich.call_count == 1
        # Both postings saved
        assert mock_save.call_count == 2
        assert result.succeeded == 2
        # 1 dedup saving (batch 2 skipped API call)
        assert result.skipped == 1


class TestPass2FallbackChain:
    """Test Pass 2 content_role_specific → full_text_raw fallback in grouping."""

    @pytest.mark.asyncio
    async def test_content_role_specific_none_falls_back_to_full_text(self):
        """When content_role_specific is None, Pass 2 groups by full_text_raw."""
        # Two postings: same title and full_text, but content_role_specific is None
        postings = [
            _make_pass2_posting(
                title="Samsung BA",
                location="Dallas, TX",
                full_text="Visit Best Buy stores.",
                content_role_specific=None,
            ),
            _make_pass2_posting(
                title="Samsung BA",
                location="Houston, TX",
                full_text="Visit Best Buy stores.",
                content_role_specific=None,
            ),
        ]

        pass2_result = _make_pass2_result()
        mock_enrich = AsyncMock(return_value=_wrap_llm(pass2_result))
        mock_resolve = AsyncMock(return_value=MagicMock(brand_id=uuid.uuid4()))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_enrich),
            patch("compgraph.enrichment.orchestrator.resolve_entity", mock_resolve),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 2
            result = await orch.run_pass2(run)

        # Only 1 API call — both grouped by full_text_raw fallback
        assert mock_enrich.call_count == 1
        assert mock_save_mentions.call_count == 2
        assert mock_mark_p2.call_count == 2
        assert result.succeeded == 2
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_different_content_role_specific_separate_groups(self):
        """Postings with different content_role_specific should be in different groups."""
        postings = [
            _make_pass2_posting(
                title="Samsung BA",
                content_role_specific="Visit Best Buy stores.",
            ),
            _make_pass2_posting(
                title="Samsung BA",
                content_role_specific="Visit Target stores.",
            ),
        ]

        pass2_result = _make_pass2_result()
        mock_enrich = AsyncMock(return_value=_wrap_llm(pass2_result))
        mock_resolve = AsyncMock(return_value=MagicMock(brand_id=uuid.uuid4()))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_enrich),
            patch("compgraph.enrichment.orchestrator.resolve_entity", mock_resolve),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 2
            result = await orch.run_pass2(run)

        # 2 API calls — different content = different groups
        assert mock_enrich.call_count == 2
        assert result.succeeded == 2
        assert result.skipped == 0


# ---------------------------------------------------------------------------
# Pass 2 fallback cache reuse test
# ---------------------------------------------------------------------------


class TestPass2FallbackCacheReuse:
    """Verify Pass 2 fallback reuses first successful result for remaining followers."""

    @pytest.mark.asyncio
    async def test_fallback_cache_reuse_skips_api_pass2(self):
        """After first follower succeeds in Pass 2 fallback, remaining reuse cache."""
        postings = [
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
        ]

        call_count = 0

        async def _failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API error")
            return _wrap_llm(_make_pass2_result())

        mock_resolve = AsyncMock(return_value=MagicMock(brand_id=uuid.uuid4()))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch(
                "compgraph.enrichment.orchestrator.enrich_posting_pass2",
                side_effect=_failing_then_succeeding,
            ),
            patch("compgraph.enrichment.orchestrator.resolve_entity", mock_resolve),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 4
            result = await orch.run_pass2(run)

        # Leader failed (1 call), first follower succeeds via API (1 call),
        # remaining 2 followers reuse cache — only 2 API calls total
        assert call_count == 2
        # 3 followers succeeded (1 via API + 2 via cache), leader failed
        assert result.succeeded == 3
        assert result.failed == 1
        # All 3 successful followers get brand mentions
        assert mock_save_mentions.call_count == 3
        assert mock_mark_p2.call_count == 3


# ---------------------------------------------------------------------------
# Skipped persistence tests
# ---------------------------------------------------------------------------


class TestSkippedPersistence:
    """Verify that dedup savings (skipped counts) are persisted to DB at finalization."""

    @pytest.mark.asyncio
    async def test_pass1_persists_skipped_count(self):
        """Finalization calls update_enrichment_run_record with pass1_skipped."""
        postings = [
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
            _make_posting(title="Samsung BA", full_text="Visit stores."),
        ]

        mock_enrich = AsyncMock(return_value=_wrap_llm(_make_pass1_result()))
        mock_save = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])
        mock_update = AsyncMock()

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass1", mock_enrich),
            patch("compgraph.enrichment.orchestrator.save_enrichment", mock_save),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_unenriched_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", mock_update),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", AsyncMock()),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            await orch.run_pass1(run)

        # The final update_enrichment_run_record call must include pass1_skipped=2
        # (3 postings, 1 API call, 2 dedup-saved)
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert "pass1_skipped" in call_kwargs
        assert call_kwargs["pass1_skipped"] == 2

    @pytest.mark.asyncio
    async def test_pass2_persists_skipped_count(self):
        """Finalization calls update_enrichment_run_record with pass2_skipped."""
        postings = [
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
            _make_pass2_posting(title="Samsung BA", content_role_specific="Visit stores."),
        ]

        pass2_result = _make_pass2_result()
        mock_enrich = AsyncMock(return_value=_wrap_llm(pass2_result))
        mock_resolve = AsyncMock(return_value=MagicMock(brand_id=uuid.uuid4()))
        mock_save_mentions = AsyncMock()
        mock_mark_p2 = AsyncMock()
        mock_fetch = AsyncMock(side_effect=[postings, []])
        mock_update = AsyncMock()

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "compgraph.enrichment.orchestrator.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch("compgraph.enrichment.orchestrator.enrich_posting_pass2", mock_enrich),
            patch("compgraph.enrichment.orchestrator.resolve_entity", mock_resolve),
            patch("compgraph.enrichment.orchestrator.save_brand_mentions", mock_save_mentions),
            patch("compgraph.enrichment.orchestrator._mark_pass2_complete", mock_mark_p2),
            patch("compgraph.enrichment.orchestrator.get_anthropic_client"),
            patch("compgraph.enrichment.orchestrator.fetch_pass1_complete_postings", mock_fetch),
            patch("compgraph.enrichment.orchestrator.update_enrichment_run_record", mock_update),
            patch("compgraph.enrichment.orchestrator.create_enrichment_run_record", AsyncMock()),
            patch("compgraph.enrichment.orchestrator.increment_enrichment_counter", AsyncMock()),
        ):
            from compgraph.enrichment.orchestrator import (
                EnrichmentOrchestrator,
                EnrichmentRun,
            )

            orch = EnrichmentOrchestrator(batch_size=10, concurrency=5)
            run = EnrichmentRun()
            run.pass1_result = MagicMock()
            run.pass1_result.failed = 0
            run.pass1_result.succeeded = 2
            await orch.run_pass2(run)

        # The final update_enrichment_run_record call must include pass2_skipped=1
        # (2 postings, 1 API call, 1 dedup-saved)
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert "pass2_skipped" in call_kwargs
        assert call_kwargs["pass2_skipped"] == 1
