import { toast } from 'sonner'
import { API_BASE } from './constants'
import { getAuthToken } from './auth-token'
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
  const token = getAuthToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...headers, ...(options?.headers as Record<string, string>) },
    })
  } catch (cause) {
    throw new Error(`Network error: ${path}`, { cause })
  }
  if (!res.ok) {
    if (res.status === 401) {
      try {
        toast.error('Your session expired. Please sign in again.')
        const { supabase } = await import('./supabase')
        await supabase?.auth.signOut()
      } catch {
        /* sign-out best-effort — import or signOut may fail */
      }
    }
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

  getPipelineStatus: () => apiFetch<PipelineStatus>('/api/v1/pipeline/status'),

  getPipelineRuns: () => apiFetch<PipelineRunsResponse>('/api/v1/pipeline/runs'),

  getVelocity: (params?: { company_id?: string; days?: number }) => {
    const q = new URLSearchParams()
    if (params?.company_id) q.set('company_id', params.company_id)
    if (params?.days) q.set('days', String(params.days))
    return apiFetch<DailyVelocity[]>(`/api/v1/aggregation/velocity${q.size ? `?${q}` : ''}`)
  },

  getBrandTimeline: (params?: { brand_id?: string }) => {
    const q = new URLSearchParams()
    if (params?.brand_id) q.set('brand_id', params.brand_id)
    return apiFetch<BrandTimeline[]>(`/api/v1/aggregation/brand-timeline${q.size ? `?${q}` : ''}`)
  },

  getPayBenchmarks: () => apiFetch<PayBenchmark[]>('/api/v1/aggregation/pay-benchmarks'),

  getLifecycle: () => apiFetch<PostingLifecycle[]>('/api/v1/aggregation/lifecycle'),

  getChurnSignals: () => apiFetch<ChurnSignal[]>('/api/v1/aggregation/churn-signals'),

  getCoverageGaps: () => apiFetch<CoverageGap[]>('/api/v1/aggregation/coverage-gaps'),

  getAgencyOverlap: () => apiFetch<AgencyOverlap[]>('/api/v1/aggregation/agency-overlap'),

  triggerAggregation: () =>
    apiFetch<{ status: string }>('/api/v1/aggregation/trigger', { method: 'POST' }),

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
    return apiFetch<PostingListResponse>(`/api/v1/postings${q.size ? `?${q}` : ''}`)
  },

  getPosting: (id: string) => apiFetch<PostingDetail>(`/api/v1/postings/${id}`),

  listEvalRuns: () => apiFetch<EvalRun[]>('/api/v1/eval/runs'),

  getEvalModels: () =>
    apiFetch<Array<{ id: string; label: string }>>('/api/v1/eval/models'),

  createEvalRun: (body: {
    pass_number: number
    model: string
    prompt_version: string
    concurrency?: number
  }) =>
    apiFetch<{ run_id: string; tracking_id: number }>('/api/v1/eval/runs', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvalRun: (id: string) => apiFetch<EvalRun>(`/api/v1/eval/runs/${id}`),

  getEvalResults: (runId: string) => apiFetch<EvalResult[]>(`/api/v1/eval/runs/${runId}/results`),

  getEvalLeaderboard: () => apiFetch<{
    runs: EvalRun[];
    elo: Record<string, number>;
    comparisons: EvalComparison[];
    field_accuracy: Record<string, Record<string, number>>;
  }>('/api/v1/eval/leaderboard-data'),

  getEloRatings: () => apiFetch<Record<string, number>>('/api/v1/eval/elo'),

  listComparisons: () => apiFetch<EvalComparison[]>('/api/v1/eval/comparisons'),

  recordComparison: (body: {
    posting_id: string
    result_a_id: string
    result_b_id: string
    winner: 'a' | 'b' | 'tie' | 'both_bad'
    notes?: string
  }) =>
    apiFetch<{ id: string }>('/api/v1/eval/comparisons', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  upsertFieldReview: (body: {
    result_id: string
    field_name: string
    is_correct: number
    notes?: string
  }) =>
    apiFetch<{ id: string }>('/api/v1/eval/field-reviews', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvalCorpus: () =>
    apiFetch<Array<{ id: string; title: string; content: string }>>('/api/v1/eval/corpus'),

  getCompanies: () =>
    apiFetch<Array<{ id: string; name: string; slug: string; ats_platform: string }>>('/api/v1/companies'),

  // Scrape control
  triggerScrape: () =>
    apiFetch<{ run_id: string; message: string }>('/api/v1/scrape/trigger', { method: 'POST' }),

  pauseScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/v1/scrape/pause', { method: 'POST' }),

  resumeScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/v1/scrape/resume', { method: 'POST' }),

  stopScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/v1/scrape/stop', { method: 'POST' }),

  forceStopScrape: () =>
    apiFetch<{ run_id: string; status: string; message: string }>('/api/v1/scrape/force-stop', { method: 'POST' }),

  getScrapeStatus: () =>
    apiFetch<ScrapeStatusResponse>('/api/v1/scrape/status'),

  // Enrichment control
  triggerEnrichment: () =>
    apiFetch<{ run_id: string; message: string }>('/api/v1/enrich/trigger', { method: 'POST' }),

  getEnrichStatus: () =>
    apiFetch<EnrichStatusResponse>('/api/v1/enrich/status'),

  // Scheduler
  getSchedulerStatus: () =>
    apiFetch<SchedulerStatusResponse>('/api/v1/scheduler/status'),

  triggerSchedulerJob: (jobId: string) =>
    apiFetch<{ job_id: string; message: string }>(`/api/v1/scheduler/jobs/${jobId}/trigger`, { method: 'POST' }),

  pauseSchedulerJob: (jobId: string) =>
    apiFetch<{ schedule_id: string; paused: boolean; message: string }>(`/api/v1/scheduler/jobs/${jobId}/pause`, { method: 'POST' }),

  resumeSchedulerJob: (jobId: string) =>
    apiFetch<{ schedule_id: string; paused: boolean; message: string }>(`/api/v1/scheduler/jobs/${jobId}/resume`, { method: 'POST' }),

  // Admin
  inviteUser: (body: { email: string; role: string }) =>
    apiFetch<{ user_id: string; email: string; role: string }>(
      '/api/v1/admin/invite',
      { method: 'POST', body: JSON.stringify(body) },
    ),
}
