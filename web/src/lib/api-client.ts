import { API_BASE } from './constants'
import type {
  PipelineStatus,
  PipelineRunsResponse,
  DailyVelocity,
  BrandTimeline,
  PayBenchmark,
  PostingLifecycle,
  ChurnSignal,
  CoverageGap,
  AgencyOverlap,
  PostingListResponse,
  PostingDetail,
  EvalRun,
  EvalResult,
  EvalComparison,
  ScrapeStatusResponse,
  EnrichStatusResponse,
  SchedulerStatusResponse,
} from './types'

/** Strip HTML/script tags from API error detail to prevent XSS if ever rendered as HTML. */
function sanitizeErrorDetail(s: string): string {
  return s.replace(/<[^>]*>/g, '').trim()
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (cause) {
    throw new Error(`Network error: ${path}`, { cause })
  }
  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = (await res.json()) as { detail?: string }
      detail = typeof body.detail === 'string' ? sanitizeErrorDetail(body.detail) : undefined
    } catch {
      /* non-JSON body — ignore */
    }
    throw new Error(detail ?? `API error ${res.status}: ${path}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => apiFetch<{ status: string; version?: string; checks?: Record<string, string> }>('/health'),

  getPipelineStatus: () => apiFetch<PipelineStatus>('/api/pipeline/status'),

  getPipelineRuns: () => apiFetch<PipelineRunsResponse>('/api/pipeline/runs'),

  getVelocity: (params?: { company_id?: string; days?: number }) => {
    const q = new URLSearchParams()
    if (params?.company_id) q.set('company_id', params.company_id)
    if (params?.days) q.set('days', String(params.days))
    return apiFetch<DailyVelocity[]>(`/api/aggregation/velocity${q.size ? `?${q}` : ''}`)
  },

  getBrandTimeline: (params?: { brand_id?: string }) => {
    const q = new URLSearchParams()
    if (params?.brand_id) q.set('brand_id', params.brand_id)
    return apiFetch<BrandTimeline[]>(`/api/aggregation/brand-timeline${q.size ? `?${q}` : ''}`)
  },

  getPayBenchmarks: () => apiFetch<PayBenchmark[]>('/api/aggregation/pay-benchmarks'),

  getLifecycle: () => apiFetch<PostingLifecycle[]>('/api/aggregation/lifecycle'),

  getChurnSignals: () => apiFetch<ChurnSignal[]>('/api/aggregation/churn-signals'),

  getCoverageGaps: () => apiFetch<CoverageGap[]>('/api/aggregation/coverage-gaps'),

  getAgencyOverlap: () => apiFetch<AgencyOverlap[]>('/api/aggregation/agency-overlap'),

  triggerAggregation: () =>
    apiFetch<{ status: string }>('/api/aggregation/trigger', { method: 'POST' }),

  listPostings: (params?: {
    limit?: number
    offset?: number
    company_id?: string
    is_active?: boolean
    role_archetype?: string
    sort_by?: string
    search?: string
  }) => {
    const q = new URLSearchParams()
    if (params?.limit !== undefined) q.set('limit', String(params.limit))
    if (params?.offset !== undefined) q.set('offset', String(params.offset))
    if (params?.company_id) q.set('company_id', params.company_id)
    if (params?.is_active !== undefined) q.set('is_active', String(params.is_active))
    if (params?.role_archetype) q.set('role_archetype', params.role_archetype)
    if (params?.sort_by) q.set('sort_by', params.sort_by)
    if (params?.search) q.set('search', params.search)
    return apiFetch<PostingListResponse>(`/api/postings${q.size ? `?${q}` : ''}`)
  },

  getPosting: (id: string) => apiFetch<PostingDetail>(`/api/postings/${id}`),

  listEvalRuns: () => apiFetch<EvalRun[]>('/api/eval/runs'),

  getEvalModels: () =>
    apiFetch<Array<{ id: string; label: string }>>('/api/eval/models'),

  createEvalRun: (body: {
    pass_number: number
    model: string
    prompt_version: string
    concurrency?: number
  }) =>
    apiFetch<{ run_id: string; tracking_id: number }>('/api/eval/runs', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvalRun: (id: string) => apiFetch<EvalRun>(`/api/eval/runs/${id}`),

  getEvalResults: (runId: string) => apiFetch<EvalResult[]>(`/api/eval/runs/${runId}/results`),

  getEvalLeaderboard: () => apiFetch<{
    runs: EvalRun[];
    elo: Record<string, number>;
    comparisons: EvalComparison[];
    field_accuracy: Record<string, Record<string, number>>;
  }>('/api/eval/leaderboard-data'),

  getEloRatings: () => apiFetch<Record<string, number>>('/api/eval/elo'),

  listComparisons: () => apiFetch<EvalComparison[]>('/api/eval/comparisons'),

  recordComparison: (body: {
    posting_id: string
    result_a_id: string
    result_b_id: string
    winner: 'a' | 'b' | 'tie' | 'both_bad'
    notes?: string
  }) =>
    apiFetch<{ id: string }>('/api/eval/comparisons', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  upsertFieldReview: (body: {
    result_id: string
    field_name: string
    is_correct: number
    notes?: string
  }) =>
    apiFetch<{ id: string }>('/api/eval/field-reviews', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvalCorpus: () =>
    apiFetch<Array<{ id: string; title: string; content: string }>>('/api/eval/corpus'),

  getCompanies: () =>
    apiFetch<Array<{ id: string; name: string; slug: string; ats_platform: string }>>('/api/companies'),

  // Scrape control
  triggerScrape: () =>
    apiFetch<{ run_id: string; message: string }>('/api/scrape/trigger', { method: 'POST' }),

  pauseScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/scrape/pause', { method: 'POST' }),

  resumeScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/scrape/resume', { method: 'POST' }),

  stopScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/scrape/stop', { method: 'POST' }),

  forceStopScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/scrape/force-stop', { method: 'POST' }),

  getScrapeStatus: () =>
    apiFetch<ScrapeStatusResponse>('/api/scrape/status'),

  // Enrichment control
  triggerEnrichment: () =>
    apiFetch<{ run_id: string; message: string }>('/api/enrich/trigger', { method: 'POST' }),

  getEnrichStatus: () =>
    apiFetch<EnrichStatusResponse>('/api/enrich/status'),

  // Scheduler
  getSchedulerStatus: () =>
    apiFetch<SchedulerStatusResponse>('/api/scheduler/status'),

  triggerSchedulerJob: (jobId: string) =>
    apiFetch<{ job_id: string; message: string }>(`/api/scheduler/jobs/${jobId}/trigger`, { method: 'POST' }),

  pauseSchedulerJob: (jobId: string) =>
    apiFetch<{ schedule_id: string; paused: boolean; message: string }>(`/api/scheduler/jobs/${jobId}/pause`, { method: 'POST' }),

  resumeSchedulerJob: (jobId: string) =>
    apiFetch<{ schedule_id: string; paused: boolean; message: string }>(`/api/scheduler/jobs/${jobId}/resume`, { method: 'POST' }),
}
