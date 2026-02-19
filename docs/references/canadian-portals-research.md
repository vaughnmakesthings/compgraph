# Research: Canadian Job Portals for Existing CompGraph Competitors

**Date:** 2026-02-19
**Researcher:** Claude (web search + codebase inspection)

## Research Question

Do the 4 current competitors (T-ROC, 2020 Companies, BDS, MarketSource) have English-language Canadian careers portals with postings not already captured by CompGraph?

## Current Scraper Configuration

| Company | ATS | Scraped URLs |
|---------|-----|-------------|
| T-ROC | Workday CXS | `troc.wd501.myworkdayjobs.com` |
| 2020 Companies | Workday CXS | `2020companies.wd1.myworkdayjobs.com` |
| BDS | iCIMS | `careers-bdssolutions.icims.com` + `careers-apolloretail.icims.com` |
| MarketSource | iCIMS | `applyatmarketsource-msc.icims.com` + `careers-marketsource.icims.com` |

## Key Findings

### 1. Workday companies (T-ROC, 2020 Companies) — LOW RISK

Workday CXS API returns **all postings** in a single paginated feed without location filtering. Our scraper pages through all results. If these companies post Canadian jobs, we are already capturing them.

**Validation needed:** Query the `postings` table for Canadian location strings (ON, BC, AB, QC, etc.) to confirm.

### 2. BDS Connected Solutions — MEDIUM RISK

Glassdoor lists "BDS (Canada) Jobs - 2 Open Positions," confirming a small Canadian presence. The 2 scraped iCIMS portals (`careers-bdssolutions.icims.com` and `careers-apolloretail.icims.com`) appear US-focused.

iCIMS commonly uses separate subdomains per country/region (as confirmed by OSL's 3-portal architecture: `uscareers-oslrs`, `canadaengcareers-oslrs`, `canadafrcareers-oslrs`). A separate Canadian iCIMS subdomain for BDS may exist.

**Portals to probe:**
- `cacareers-bdssolutions.icims.com`
- `canadaengcareers-bdssolutions.icims.com`
- `canadacareers-bdssolutions.icims.com`
- `cacareers-apolloretail.icims.com`

### 3. MarketSource — LOW RISK

No evidence of Canadian operations. MarketSource (an Allegis Group company) appears to operate exclusively in the US for B2B and retail sales acceleration. No Canadian-specific search results found.

**Portals to probe (low priority):**
- `cacareers-marketsource.icims.com`
- `cacareers-msc.icims.com`

### 4. T-ROC — LOW RISK

Uses `jobs.trocglobal.com` (branded) and `troc.wd501.myworkdayjobs.com` (Workday CXS). The "Global" branding suggests international ambitions, but all found job listings are US-focused. Workday CXS scraper captures all postings regardless.

### 5. 2020 Companies — LOW RISK

No Canadian-specific results found. Workday CXS scraper captures all postings regardless.

## Relevance to CompGraph

- **iCIMS risk**: The iCIMS platform's multi-subdomain architecture means Canadian portals (if they exist) are completely invisible to our current scraper config. This is a configuration gap, not a code gap — adding a new `search_urls` entry would capture them.
- **Workday coverage**: Already comprehensive by design. The CXS API returns all postings in one feed.
- **Magnitude**: Even if BDS has a Canadian portal, it likely has very few postings (Glassdoor shows only 2). The ROI of adding it is low compared to OSL (750+ postings across 3 portals).

## Recommended Actions

- [ ] **Query postings table** for Canadian location strings in T-ROC and 2020 Companies data to confirm existing coverage
- [ ] **Browser-probe BDS iCIMS subdomains** (cacareers-bdssolutions, canadaengcareers-bdssolutions, canadacareers-bdssolutions) — 30-second check
- [ ] **Browser-probe MarketSource iCIMS subdomains** (cacareers-marketsource, cacareers-msc) — low priority
- [ ] **Defer Canadian portal expansion** until after OSL onboarding is complete (OSL has 750+ postings vs BDS's ~2 Canadian jobs)

## Open Questions

- Does BDS have a Canadian iCIMS subdomain? (2 Glassdoor jobs suggest possible, but could be US portal cross-posts)
- Are the Workday scrapers already capturing Canadian postings? (Need DB query to confirm)
- Are the 2 BDS Canada Glassdoor jobs from BDS's main US portal or a separate Canadian portal?
