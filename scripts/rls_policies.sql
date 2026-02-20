-- CompGraph Row-Level Security Policies
-- Issue #52: Supabase security hardening
--
-- Strategy: Deny all access through Supabase REST API (anon/service_role keys).
-- The app connects via session-mode pooler as `postgres` user, which bypasses RLS.
-- These policies protect against leaked Supabase anon/service_role keys only.
--
-- Roles:
--   anon            -> no access (no policies grant to anon)
--   authenticated   -> SELECT only on app tables; own-row only on users
--   service_role    -> bypasses RLS (Supabase default)
--   postgres        -> bypasses RLS (table owner, used by app via pooler)
--
-- Usage:
--   psql $DATABASE_URL -f scripts/rls_policies.sql
--   OR: op run --env-file=.env -- psql $DATABASE_URL_DIRECT -f scripts/rls_policies.sql

BEGIN;

-- =============================================================================
-- 1. Enable RLS on all application tables
-- =============================================================================

-- Dimension tables
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE retailers ENABLE ROW LEVEL SECURITY;
ALTER TABLE markets ENABLE ROW LEVEL SECURITY;

-- Operational tables
ALTER TABLE scrape_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrichment_runs ENABLE ROW LEVEL SECURITY;

-- Fact tables
ALTER TABLE postings ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_enrichments ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_brand_mentions ENABLE ROW LEVEL SECURITY;

-- Aggregation tables
ALTER TABLE agg_daily_velocity ENABLE ROW LEVEL SECURITY;
ALTER TABLE agg_brand_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE agg_pay_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE agg_posting_lifecycle ENABLE ROW LEVEL SECURITY;

-- Auth table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 2. SELECT-only policies for authenticated users
-- =============================================================================

-- Dimension tables
DROP POLICY IF EXISTS read_companies ON companies;
CREATE POLICY read_companies ON companies FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_brands ON brands;
CREATE POLICY read_brands ON brands FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_retailers ON retailers;
CREATE POLICY read_retailers ON retailers FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_markets ON markets;
CREATE POLICY read_markets ON markets FOR SELECT TO authenticated USING (true);

-- Operational tables
DROP POLICY IF EXISTS read_scrape_runs ON scrape_runs;
CREATE POLICY read_scrape_runs ON scrape_runs FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_enrichment_runs ON enrichment_runs;
CREATE POLICY read_enrichment_runs ON enrichment_runs FOR SELECT TO authenticated USING (true);

-- Fact tables
DROP POLICY IF EXISTS read_postings ON postings;
CREATE POLICY read_postings ON postings FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_posting_snapshots ON posting_snapshots;
CREATE POLICY read_posting_snapshots ON posting_snapshots FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_posting_enrichments ON posting_enrichments;
CREATE POLICY read_posting_enrichments ON posting_enrichments FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_posting_brand_mentions ON posting_brand_mentions;
CREATE POLICY read_posting_brand_mentions ON posting_brand_mentions FOR SELECT TO authenticated USING (true);

-- Aggregation tables
DROP POLICY IF EXISTS read_agg_daily_velocity ON agg_daily_velocity;
CREATE POLICY read_agg_daily_velocity ON agg_daily_velocity FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_agg_brand_timeline ON agg_brand_timeline;
CREATE POLICY read_agg_brand_timeline ON agg_brand_timeline FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_agg_pay_benchmarks ON agg_pay_benchmarks;
CREATE POLICY read_agg_pay_benchmarks ON agg_pay_benchmarks FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS read_agg_posting_lifecycle ON agg_posting_lifecycle;
CREATE POLICY read_agg_posting_lifecycle ON agg_posting_lifecycle FOR SELECT TO authenticated USING (true);

-- Users table: authenticated users can only see their own record
DROP POLICY IF EXISTS read_own_user ON users;
CREATE POLICY read_own_user ON users FOR SELECT TO authenticated USING (auth.uid() = id);

COMMIT;
