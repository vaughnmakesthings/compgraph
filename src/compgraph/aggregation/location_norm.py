"""Shared location normalization SQL for aggregation jobs.

Matches seed_location_mappings / normalize_location_raw: strips country suffix,
ZIP codes, company suffixes, and normalizes whitespace. Used by coverage_gaps
and pay_benchmarks to join against location_mappings.
Expects `ls` in scope with `location_raw` (e.g. latest_snapshots).
"""

# Fragment to embed: REGEXP_REPLACE(...) chain. Use as SPLIT_PART({_LOC_NORM_SQL}, ',', 1) etc.
_LOC_NORM_SQL = """REGEXP_REPLACE(
    REGEXP_REPLACE(
        REGEXP_REPLACE(
            REGEXP_REPLACE(COALESCE(ls.location_raw, ''), ',\\s*(US|CA)\\s*$', '', 'i'),
            '\\s+\\d{5}(-\\d{4})?', '', 'g'),
        '\\s*[-\x2013\x2014]\\s*(2020 companies|bds connected solutions|marketsource|'
        't-roc|mosaic sales solutions|advantage solutions|acosta)\\s*$', '', 'i'),
    '\\s+', ' ', 'g')"""
