export interface PipelineStatus {
  status: 'idle' | 'scraping' | 'enriching' | 'aggregating'
  scrape: {
    current_run: { postings_found: number; snapshots_created: number } | null
    last_completed_at: string | null
    next_run_at: string | null
  }
  enrich: {
    current_run: { pass1_completed: number; pass2_completed: number } | null
    last_completed_at: string | null
  }
  scheduler: { next_run_at: string | null }
}

export interface DailyVelocity {
  date: string
  company_id: string
  company_name?: string
  company_slug?: string
  new_postings: number
  closed_postings: number
  active_postings: number
}

export interface BrandTimeline {
  brand_id: string
  brand_name: string
  date: string
  posting_count: number
  company_id: string
  company_name?: string
  company_slug?: string
}

export interface PayBenchmark {
  company_id: string
  role_archetype: string
  pay_min_avg: number | null
  pay_max_avg: number | null
  sample_size: number
}

export interface PostingLifecycle {
  company_id: string
  role_archetype: string
  avg_days_open: number | null
  median_days_open: number | null
  repost_rate: number | null
}

export interface ChurnSignal {
  brand_id: string
  brand_name: string
  company_id: string
  first_seen: string
  last_seen: string
  days_since_last_posting: number
}

export interface CoverageGap {
  market: string
  state: string
  companies_present: string[]
  companies_absent: string[]
}

export interface AgencyOverlap {
  brand_id: string
  brand_name: string
  company_ids: string[]
  company_count: number
}

export interface PostingListItem {
  id: string
  company_id: string
  title: string | null
  location: string | null
  first_seen_at: string
  last_seen_at: string | null
  is_active: boolean
  role_archetype: string | null
  pay_min: number | null
  pay_max: number | null
  employment_type: string | null
}

export interface PostingListResponse {
  items: PostingListItem[]
  total: number
}

export interface PostingDetail extends PostingListItem {
  url: string | null
  enrichment: {
    role_archetype: string | null
    pay_min: number | null
    pay_max: number | null
    employment_type: string | null
    work_model: string | null
    enrichment_version: string | null
  } | null
  brand_mentions: Array<{
    brand_id: string
    brand_name: string
    mention_type: string
  }>
}

export interface EvalRun {
  id: string
  pass_number: number
  model: string
  prompt_version: string
  status: string
  created_at: string
  completed_at: string | null
  total_items: number
  completed_items: number
}

export interface EvalResult {
  id: string
  run_id: string
  posting_id: string
  raw_response: string | null
  parsed_result: Record<string, unknown> | null
  parse_success: boolean
  input_tokens: number | null
  output_tokens: number | null
  cost_usd: number | null
  latency_ms: number | null
  created_at: string | null
}

export interface EvalComparison {
  id: string
  posting_id: string
  result_a_id: string
  result_b_id: string
  winner: 'a' | 'b' | 'tie' | 'both_bad'
  notes: string | null
  created_at: string
}
