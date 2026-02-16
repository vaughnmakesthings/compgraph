"""Tests for backfill enrichment script."""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_default_args(self):
        from scripts.backfill_enrichment import parse_args

        with patch("sys.argv", ["backfill"]):
            args = parse_args()

        assert args.company_id is None
        assert args.batch_size is None
        assert args.concurrency is None
        assert args.pass1_only is False
        assert args.pass2_only is False
        assert args.dry_run is False

    def test_dry_run_flag(self):
        from scripts.backfill_enrichment import parse_args

        with patch("sys.argv", ["backfill", "--dry-run"]):
            args = parse_args()

        assert args.dry_run is True

    def test_pass1_only_flag(self):
        from scripts.backfill_enrichment import parse_args

        with patch("sys.argv", ["backfill", "--pass1-only"]):
            args = parse_args()

        assert args.pass1_only is True

    def test_pass2_only_flag(self):
        from scripts.backfill_enrichment import parse_args

        with patch("sys.argv", ["backfill", "--pass2-only"]):
            args = parse_args()

        assert args.pass2_only is True

    def test_batch_size_override(self):
        from scripts.backfill_enrichment import parse_args

        with patch("sys.argv", ["backfill", "--batch-size", "25"]):
            args = parse_args()

        assert args.batch_size == 25


# ---------------------------------------------------------------------------
# Backfill run logic
# ---------------------------------------------------------------------------


class TestRunBackfill:
    @pytest.mark.asyncio
    async def test_dry_run_skips_processing(self):
        from scripts.backfill_enrichment import run_backfill

        args = argparse.Namespace(
            company_id=None,
            batch_size=None,
            concurrency=None,
            pass1_only=False,
            pass2_only=False,
            dry_run=True,
        )

        with patch(
            "scripts.backfill_enrichment.count_unenriched",
            new_callable=AsyncMock,
            return_value={
                "total_active": 100,
                "need_pass1": 50,
                "need_pass2": 30,
                "need_fingerprint": 80,
            },
        ):
            exit_code = await run_backfill(args)

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_no_active_postings(self):
        from scripts.backfill_enrichment import run_backfill

        args = argparse.Namespace(
            company_id=None,
            batch_size=None,
            concurrency=None,
            pass1_only=False,
            pass2_only=False,
            dry_run=False,
        )

        with patch(
            "scripts.backfill_enrichment.count_unenriched",
            new_callable=AsyncMock,
            return_value={
                "total_active": 0,
                "need_pass1": 0,
                "need_pass2": 0,
                "need_fingerprint": 0,
            },
        ):
            exit_code = await run_backfill(args)

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_pass1_only_runs_pass1(self):
        from compgraph.enrichment.orchestrator import EnrichResult
        from scripts.backfill_enrichment import run_backfill

        args = argparse.Namespace(
            company_id=None,
            batch_size=10,
            concurrency=2,
            pass1_only=True,
            pass2_only=False,
            dry_run=False,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.run_pass1 = AsyncMock(return_value=EnrichResult(succeeded=5, failed=1))

        with (
            patch(
                "scripts.backfill_enrichment.count_unenriched",
                new_callable=AsyncMock,
                return_value={
                    "total_active": 10,
                    "need_pass1": 6,
                    "need_pass2": 0,
                    "need_fingerprint": 10,
                },
            ),
            patch(
                "compgraph.enrichment.orchestrator.EnrichmentOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            exit_code = await run_backfill(args)

        assert exit_code == 0
        mock_orchestrator.run_pass1.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pass2_only_runs_pass2(self):
        from compgraph.enrichment.orchestrator import EnrichResult
        from scripts.backfill_enrichment import run_backfill

        args = argparse.Namespace(
            company_id=None,
            batch_size=None,
            concurrency=None,
            pass1_only=False,
            pass2_only=True,
            dry_run=False,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.run_pass2 = AsyncMock(return_value=EnrichResult(succeeded=3, failed=0))

        with (
            patch(
                "scripts.backfill_enrichment.count_unenriched",
                new_callable=AsyncMock,
                return_value={
                    "total_active": 10,
                    "need_pass1": 0,
                    "need_pass2": 3,
                    "need_fingerprint": 10,
                },
            ),
            patch(
                "compgraph.enrichment.orchestrator.EnrichmentOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            exit_code = await run_backfill(args)

        assert exit_code == 0
        mock_orchestrator.run_pass2.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_runs_all(self):
        from compgraph.enrichment.orchestrator import EnrichResult
        from scripts.backfill_enrichment import run_backfill

        args = argparse.Namespace(
            company_id=None,
            batch_size=None,
            concurrency=None,
            pass1_only=False,
            pass2_only=False,
            dry_run=False,
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.run_full = AsyncMock(
            return_value=(
                EnrichResult(succeeded=10, failed=0),
                EnrichResult(succeeded=8, failed=2),
            )
        )

        with (
            patch(
                "scripts.backfill_enrichment.count_unenriched",
                new_callable=AsyncMock,
                return_value={
                    "total_active": 20,
                    "need_pass1": 10,
                    "need_pass2": 10,
                    "need_fingerprint": 20,
                },
            ),
            patch(
                "compgraph.enrichment.orchestrator.EnrichmentOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            exit_code = await run_backfill(args)

        assert exit_code == 0
        mock_orchestrator.run_full.assert_awaited_once()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_keyboard_interrupt_returns_130(self):
        from scripts.backfill_enrichment import main

        with (
            patch("sys.argv", ["backfill"]),
            patch("scripts.backfill_enrichment.asyncio.run", side_effect=KeyboardInterrupt),
        ):
            exit_code = main()

        assert exit_code == 130
