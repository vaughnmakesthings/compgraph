# CompGraph — Project Context & Strategic Direction

> **Document purpose:** Primary context document for Claude Code agents working on CompGraph. Read this FIRST before any implementation work. Contains product strategy, user mental models, data architecture decisions, and technical constraints that should inform every PR.
>
> **Owner:** Vaughn (Founder / Product Lead)
> **Last updated:** 2026-02-20
> **Classification:** Internal — do not expose in client-facing output

---

## 1. What CompGraph Is

CompGraph is a competitive intelligence platform for the field marketing industry. It monitors the hiring activity of competing agencies by scraping their public job postings, then uses LLM enrichment to extract structured signals: which brands they service, which retailers they operate in, how aggressively they're hiring, and where they're expanding geographically.

**It is NOT a generic analytics dashboard.** It is a sales intelligence and opportunity identification tool. Every feature should answer a question that helps the BD team win business.

### The Organization

CompGraph is built inside **Mosaic Sales Solutions**, a division of Acosta Group. Mosaic is a national field marketing agency that runs retail programs for Fortune 500 brands (OtterBox, Google, Samsung, Microsoft, Whirlpool, Verizon, Discover Card) across carrier channels and consumer electronics retailers.

Mosaic competes with other field marketing agencies for brand contracts. CompGraph exists to give Mosaic's leadership an information advantage over those competitors.

### The Competitive Landscape CompGraph Monitors

**Tier 1 nationals** (MarketSource, Advantage Solutions, etc.) — Mosaic leadership already has strong informal intelligence on these through industry relationships and daily market presence. CompGraph captures their data but the *primary value proposition* is illuminating the next tier.

**Regional and mid-market players** — This is where the blind spot is. Smaller agencies win brand business, expand into adjacent markets, and build client relationships largely outside Mosaic's visibility. By the time leadership learns about these movements through informal channels, the opportunity window may have narrowed. CompGraph closes this gap.

### Initial Target Agencies (v1 Scraping Targets)

| Agency | ATS Platform | Career Site | Scraper Adapter |
|--------|-------------|-------------|-----------------|
| MarketSource | iCIMS | `applyatmarketsource-msc.icims.com` | iCIMS portal scraper |
| BDS Connected Solutions | iCIMS | `careers-bdssolutions.icims.com` | iCIMS portal scraper |
| 2020 Companies | Workday | `wd1.myworkdayjobs.com` (TBD exact path) | Workday CXS API scraper |
| T-ROC Global | Custom | `jobs.trocglobal.com` | Needs discovery |

**Architecture constraint:** The system MUST be designed so new agencies can be added without code changes to the frontend or aggregation layer. Agency list is configuration, not code.

**Note:** ActionLink and Premium Retail Services are Mosaic's *sister agencies* (same parent company, Acosta Group) — they are NOT competitors and should NOT be tracked.

---

## 2. Users and Their Mental Models

There are two primary user types. Their needs are different and the UI must serve both.

### User Type A: Agency Presidents & Regional Vice Presidents

**Interaction pattern:** Periodic strategic review. Weekly or biweekly check-ins.

**Mental model:** "What changed in my competitive landscape since I last looked?"

**What they need from CompGraph:**
- High-level view of competitive activity across their geography
- Alerts when a new competitor enters their market or a known competitor expands
- Trend data: are competitors growing or contracting in specific verticals?
- Presentation-ready views they can reference in leadership meetings
- Confidence-scored intelligence — they will NOT act on unvalidated signals

**What they do NOT need:**
- Raw data tables
- Technical detail on data sources
- Ability to drill into individual job postings (though this should be available if they want it)

**UX implication:** The Signals Feed (View 4) is their primary entry point. It should answer "what changed this week" in under 30 seconds of scanning.

### User Type B: Business Development & Growth Officers

**Interaction pattern:** Active, daily research. They dig into specific agencies, brands, and markets to build pipeline.

**Mental model:** "Help me find and qualify my next opportunity."

**What they need from CompGraph:**
- Searchable agency dossiers: every brand relationship, retailer presence, geographic footprint
- Brand-level intelligence: which agencies service a target brand, where are the gaps?
- Opportunity scoring: which brand-agency pairings represent realistic displacement targets?
- Evidence trails: every insight links to its source job postings so they can validate before a pitch
- Filtering across every dimension: agency → brand → retailer → geography → vertical → time

**What they do NOT need:**
- Simplified views that hide data
- Opinionated dashboards that pre-filter too aggressively

**UX implication:** The Opportunity Finder (View 1) and Agency Profiles (View 2) are their primary entry points. These need to be data-dense but scannable.

---

## 3. The Goal — What Problem We're Solving

CompGraph answers four strategic questions for Mosaic leadership:

1. **Offense:** Which brands are being serviced by regional agencies we can displace?
2. **Defense:** Which competitors are expanding into our markets or verticals?
3. **Market mapping:** Who operates where, across which retailers and verticals, with what brands?
4. **Speed:** Surface opportunities and threats in near real-time vs. quarterly industry chatter.

### Success criteria (qualitative, for agent decision-making)

A feature is valuable if it helps a user identify and target an competing agency's client. A feature is also valuable if it gives the user visibility into what is happening within the competitors business without manual research.  A feature is NOT valuable if it just visualizes data without connecting it to an actionable opportunity.

When making architecture or UX decisions, ask: "Does this help someone at Mosaic win a brand contract they wouldn't have won otherwise?"

---

## 4. Current Data Model — What We Capture Today

### Per Job Posting (raw scrape)

| Field | Source | Type | Notes |
|-------|--------|------|-------|
| `job_title` | Direct scrape | `string` | Verbatim from listing |
| `location` | Direct scrape | `string` | City/state, sometimes zip. Needs normalization. |
| `description` | Direct scrape | `text` | Full HTML or plain text of job description |
| `pay_rate` | Direct scrape | `string \| null` | When disclosed. Format varies (hourly, salary, range). Partial coverage. |
| `source_url` | Direct scrape | `string` | Permalink to original listing |
| `agency` | Known from scraper config | `string` | Which competitor posted this |
| `ats_platform` | Known from scraper config | `string` | iCIMS, Workday, etc. |
| `first_observed_at` | System-generated | `datetime` | When our scraper first saw this listing |
| `closed_at` | System-generated | `datetime \| null` | When listing disappeared from careers page |

### Per Job Posting (LLM enrichment — two-pass pipeline)

| Field | LLM Pass | Type | Confidence | Notes |
|-------|----------|------|------------|-------|
| `role_archetype` | Pass 1 | `enum` | Medium-High | Standardized categories: Retail Sales Specialist, Account Manager, Merchandiser, Demo Specialist, etc. |
| `client_brands` | Pass 2 | `string[]` | Medium | Extracted brand names mentioned in description. Confidence varies by description specificity. |
| `retailers` | Pass 2 | `string[]` | Medium | Extracted retailer names. Same confidence caveat. |

### Derived / Aggregated (computed from above)

| Signal | Derivation | Confidence |
|--------|-----------|------------|
| Hiring velocity | Count of open postings per agency per market over time | High — direct from data |
| Role mix | Distribution of role archetypes per agency | High — direct from data |
| Geographic footprint | Unique locations per agency | High — direct from data |
| Role lifecycle | Time between `first_observed_at` and `closed_at` | High — direct from data |
| Compensation benchmarks | Aggregated pay rates where available | Medium — partial coverage |
| Brand-agency relationships | Aggregated `client_brands` across postings | Medium — LLM-dependent |
| Retailer presence | Aggregated `retailers` across postings | Medium — LLM-dependent |
| Vertical specialization | Derived from brand + retailer tags | Low-Medium — double inference |

### Critical UX Constraint: Evidence Trails

**Every inferred relationship in the UI MUST display:**

1. **Evidence count** — "Based on 7 postings"
2. **Recency** — "Last seen: 2 weeks ago" vs. "Last seen: 8 months ago"
3. **Clickable source trail** — Links to the actual job postings supporting the claim

**Rationale:** Agency presidents will reference this data in meetings with their leadership chain. If a brand-agency relationship is inferred from a single vague job posting, the user MUST know that before acting on it. This is a trust feature, not a nice-to-have.

---

## 5. Frontend Architecture — Four Core Views

### View 1: Opportunity Finder

**The primary working screen for BD officers.**

Surfaces brand-agency pairings where a regional player is servicing a brand Mosaic could target. The mental model is a prioritized opportunity list, not a data explorer.

- Filterable by: retailer, vertical, geography, agency size, evidence strength
- Each opportunity row shows: agency name, brand, retailer(s), markets, evidence count, last seen date
- Click-through to Agency Profile or Brand Intelligence view
- Sorting by displacement potential / opportunity score (future enhancement — initially sort by evidence count and recency)

### View 2: Agency Profiles

**Dossier-style pages for each monitored competitor.**

One page per agency. The BD team opens this before a pitch meeting to understand who they're competing against.

Contents:
- Agency summary: name, estimated scale, primary verticals, headquarters
- Brand relationships (with evidence counts and recency for each)
- Retailer footprint (which retailers they operate in, with geographic breakdown)
- Hiring activity: trend chart of open postings over time, current volume
- Geographic concentration: map or list of markets with posting density
- Role mix: breakdown by archetype (indicates program sophistication)
- Pay rate data: where available, aggregated ranges
- Vertical tags: CE, wireless, appliance, beauty, food/bev, etc.

### View 3: Brand Intelligence

**Reverse lens — brand-centric rather than agency-centric.**

Select a brand, see which agencies service it across retailers and markets. Identifies coverage gaps that represent opportunities for Mosaic.

- Brand search/browse
- For each brand: list of agencies servicing it, with evidence strength
- Geographic heatmap of where each agency services that brand
- Retailer breakdown per agency
- Gap analysis: markets/retailers where no agency appears (or only weak signals exist)

### View 4: Signals Feed

**"What changed this week" for time-constrained executives.**

Prioritized feed of notable changes:
- New brand-agency relationships detected
- Hiring surges (agency posting volume > 2x trailing average)
- New geographic markets for an agency
- Roles closing faster than usual (could indicate program churn)
- New agencies entering monitored space

Feed items should be concise (one-line headline + supporting detail on expand) and link to the relevant Agency Profile or Brand Intelligence view.

---

## 6. Tech Stack Decisions

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | **Next.js 14+ (App Router)** | Server components for data-heavy views. Will be deployed standalone. |
| UI components | **shadcn/ui** | Best AI-assisted generation quality. Tailwind-native. |
| Styling | **Tailwind CSS** | Consistent with shadcn/ui. Utility-first. |
| Charts | **Recharts** | Best integration with shadcn/ui ecosystem. SSR-compatible. |
| Icons | **Lucide React** | Default for shadcn/ui projects. |
| Language | **TypeScript** | Non-negotiable for a data-heavy app with complex types. |
| Auth | **TBD** | Magic link / invite-only. Role-based: president vs. BD may see different defaults. |
| Deployment | **TBD** | Vercel or self-hosted (Raspberry Pi server exists for dev). |

### Design System Constraints

- **Aesthetic:** Executive, hyper-minimalist. Not a developer tool. Must look polished in a conference room.
- **Color:** Restrained palette. Slate/gray neutrals, single blue accent (`#2563EB`). Data visualization uses a carefully chosen multi-color palette for category differentiation.
- **Typography:** `font-semibold` for headings, `font-normal` for body, `text-muted-foreground` for labels. `text-2xl font-bold` for metric values.
- **Spacing:** `p-4`/`p-6` on cards, `gap-4`/`gap-6` on grids. Generous whitespace.
- **Cards:** White background, `rounded-lg`, `shadow-sm`. No heavy borders.
- **Dark mode:** Support from day one. Dark mode should be the default for data-dense views.
- **Responsive:** Desktop-first (this is used in offices), but must not break on tablet (for conference room iPad scenarios).

---

## 7. Data Enrichment Roadmap — Future Intelligence Sources

The system architecture MUST be **source-agnostic from day one**. A brand-agency relationship is a `relationship` entity regardless of whether it originated from a job posting, a press release, a LinkedIn profile, or a government contract. Adding new sources should NOT require frontend changes — only new enrichment pipeline adapters and potentially new confidence weights.

### Phase 1 — Near-Term (Validates existing data)

| Source | Value | Approach | Cost |
|--------|-------|----------|------|
| **Competitor websites** (client/case study pages) | Direct validation of brand-agency relationships. Many agencies list client logos publicly. | Custom scraper per site. Periodic (monthly). | Free |
| **Press releases & news** | Confirmed client wins, partnership announcements. Highest-confidence source for brand-agency relationships. | Google News API + keyword monitoring on competitor names. | Low (API costs) |
| **Google Jobs / Indeed** | Cross-posted jobs broaden coverage. Catches agencies using ATS platforms we haven't mapped. | Structured API integration. | Low-Medium |

### Phase 2 — Next Sprint (New intelligence dimensions)

| Source | Value | Approach | Cost |
|--------|-------|----------|------|
| **LinkedIn company pages** | Employee headcount trends validate hiring velocity. Senior hire tracking surfaces strategic moves. | Third-party enrichment providers (Coresignal, Proxycurl). | Medium |
| **Glassdoor / Indeed reviews** | Employee reviews name clients and retailers. Sentiment scoring = morale signal (low morale = displacement opportunity). | Scrape + LLM extraction. Reuses existing pipeline. | Low |
| **Brand career pages** | Brands posting for "field marketing agency manager" = active RFP signal. | Reuse existing scraper framework with new targets. | Free |
| **Trade show exhibitor lists** | Which regional players are investing in industry visibility. | Annual scrape of CEMA, Shop!, Path to Purchase exhibitor pages. | Free |

### Phase 3 — Future (Intel → Pipeline)

| Source | Value | Approach | Cost |
|--------|-------|----------|------|
| **Contact enrichment (Apollo.io)** | Verified contacts at target brands — VP Field Marketing, Channel Sales Directors. Transforms CompGraph from intelligence to actionable BD pipeline. | Apollo API. Free tier: 50 credits/mo. Basic: $49/user/mo for 5K email credits. | Low-Medium |
| **SEC / public filings** | Revenue concentration, key client disclosures for publicly traded competitors. | SEC EDGAR API (free). LLM extraction from filing text. | Free |
| **Government contracts (SAM.gov)** | Federal contract awards for retail programs. Fully structured: contractor, value, duration. | Public API. | Free |
| **D&B / Crunchbase** | Revenue estimates, employee counts, subsidiary structures for private agencies. | API. Validates agency scale. | Medium |

### Phase 4 — Evaluate After Core Proves Value

| Source | Value | Approach | Cost |
|--------|-------|----------|------|
| **Retail data (Placer.ai)** | Store count and foot traffic by retailer/region. Overlay with competitor footprint. | API subscription. | High |
| **Social media monitoring** | Geo-tagged field activity from agency employees. | API + NLP pipeline. | Medium |
| **LinkedIn Sales Navigator** | Advanced prospecting for brand contacts. | Enterprise license. | High |

### Data Model Implication

Every relationship in the system should carry:

```typescript
interface RelationshipEvidence {
  source_type: 'job_posting' | 'press_release' | 'website' | 'glassdoor' | 'linkedin' | 'sec_filing' | 'government_contract' | 'trade_show' | 'brand_career_page' | 'contact_enrichment';
  source_url: string;
  source_date: Date;
  extraction_confidence: number; // 0-1
  extraction_method: 'direct_scrape' | 'llm_inference' | 'api_structured';
}

interface BrandAgencyRelationship {
  agency_id: string;
  brand_name: string;
  retailers: string[];
  markets: string[]; // geographic
  evidence: RelationshipEvidence[];
  first_detected: Date;
  last_confirmed: Date;
  evidence_count: number; // denormalized for query performance
  composite_confidence: number; // weighted across all evidence
}
```

This structure ensures that when Phase 2/3 sources come online, they add evidence to existing relationships (increasing confidence) or create new ones — without schema changes.

---

## 8. Scraping & Pipeline Architecture Notes

### Scrape Frequency
- **Daily** — overnight scrape cycle, data ready by morning
- IP blocking mitigation required (rotating proxies, request throttling, user-agent rotation)
- Scraper failures should be monitored and alerted

### LLM Enrichment Pipeline
- **Two-pass architecture:** Pass 1 (role archetype classification) → Pass 2 (brand/retailer extraction)
- **Model strategy:** Haiku for simple classification (Pass 1), Sonnet for complex extraction (Pass 2). Cost optimization via prompt caching and batching.
- **Error handling:** Failed enrichments should be queued for retry, not silently dropped

### Data Quality
- Brand/retailer taxonomy management needed (merge duplicates, correct misclassifications)
- Role archetype normalization across agencies (same role, different titles)
- Pay rate format normalization (hourly/salary/range → structured fields)

---

## 9. Open Questions & Future Decisions

| Question | Context | Status |
|----------|---------|--------|
| Auth approach | Magic link + invite-only vs. SSO. Role-based views (president vs BD). | TBD — implement after core views work |
| Deployment target | Vercel (quick) vs. self-hosted (control). Dev server exists on Raspberry Pi. | TBD |
| Agency list management | How do new agencies get added? Config file vs. admin UI. | Leaning config file for v1 |
| Notification system | Email/Slack alerts for Signals Feed items | Phase 2 feature |
| Export / presentation mode | PDF export of Agency Profiles for pitch prep | Phase 2 feature |
| Opportunity scoring algorithm | How to rank displacement opportunities | Needs real data to inform — start with evidence count + recency as proxy |
| Historical data retention | How far back to keep closed postings | Keep everything — storage is cheap, historical trends are valuable |

---

## 10. What "Done" Looks Like for v1

The minimum viable CompGraph frontend is complete when:

1. All four views (Opportunity Finder, Agency Profiles, Brand Intelligence, Signals Feed) are functional with real data
2. Evidence trails work end-to-end (click from a relationship to its source postings)
3. Filtering works across all core dimensions (agency, brand, retailer, geography, time)
4. The UI passes the "conference room test" — a president can pull it up in a meeting and it looks credible
5. Data refreshes daily without manual intervention
6. At least 4 competing agencies are actively monitored with enriched data

**What is explicitly NOT in v1:** Auth/roles, notifications, PDF export, contact enrichment, any Phase 2+ data sources, mobile optimization, opportunity scoring beyond simple heuristics.
