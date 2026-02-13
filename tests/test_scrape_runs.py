from __future__ import annotations

import uuid
from datetime import UTC, datetime

from compgraph.db.models import Company, ScrapeRun


class TestScrapeRunModel:
    def test_instantiation_with_required_fields(self):
        company_id = uuid.uuid4()
        started = datetime.now(UTC)
        run = ScrapeRun(
            company_id=company_id,
            started_at=started,
            status="pending",
        )

        assert run.company_id == company_id
        assert run.status == "pending"
        assert run.started_at == started
        assert run.errors is None
        assert run.completed_at is None

    def test_instantiation_with_all_fields(self):
        company_id = uuid.uuid4()
        started = datetime.now(UTC)
        completed = datetime.now(UTC)
        errors_payload = {"errors": ["timeout", "rate limited"]}

        run = ScrapeRun(
            company_id=company_id,
            started_at=started,
            completed_at=completed,
            status="failed",
            pages_scraped=5,
            jobs_found=42,
            snapshots_created=38,
            errors=errors_payload,
        )

        assert run.status == "failed"
        assert run.pages_scraped == 5
        assert run.jobs_found == 42
        assert run.snapshots_created == 38
        assert run.errors == errors_payload
        assert run.completed_at == completed

    def test_status_pending_to_completed(self):
        run = ScrapeRun(
            company_id=uuid.uuid4(),
            started_at=datetime.now(UTC),
            status="pending",
        )
        assert run.status == "pending"

        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.jobs_found = 25
        run.snapshots_created = 25

        assert run.status == "completed"
        assert run.completed_at is not None
        assert run.jobs_found == 25

    def test_status_pending_to_failed(self):
        run = ScrapeRun(
            company_id=uuid.uuid4(),
            started_at=datetime.now(UTC),
            status="pending",
        )
        assert run.status == "pending"

        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        run.errors = {"errors": ["Connection refused"]}

        assert run.status == "failed"
        assert run.errors is not None
        assert "Connection refused" in run.errors["errors"]

    def test_relationship_to_company_via_id(self):
        company = Company(
            name="Test Co",
            slug="test-co",
            ats_platform="icims",
            career_site_url="https://example.com",
        )
        run = ScrapeRun(
            company_id=company.id,
            started_at=datetime.now(UTC),
            status="pending",
        )

        assert run.company_id == company.id

    def test_table_name(self):
        assert ScrapeRun.__tablename__ == "scrape_runs"

    def test_errors_column_accepts_nested_json(self):
        errors_payload = {
            "errors": ["timeout"],
            "metadata": {"attempt": 3, "last_status_code": 503},
        }
        run = ScrapeRun(
            company_id=uuid.uuid4(),
            started_at=datetime.now(UTC),
            status="failed",
            errors=errors_payload,
        )
        assert run.errors["metadata"]["attempt"] == 3


class TestScrapeResultPagesScraped:
    def test_pages_scraped_default(self):
        from compgraph.scrapers.base import ScrapeResult

        result = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="test",
        )
        assert result.pages_scraped == 0

    def test_pages_scraped_set(self):
        from compgraph.scrapers.base import ScrapeResult

        result = ScrapeResult(
            company_id=uuid.uuid4(),
            company_slug="test",
            pages_scraped=7,
        )
        assert result.pages_scraped == 7
