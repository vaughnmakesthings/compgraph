import { API_BASE } from './constants'
import type {
  PipelineStatus,
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
  EvalComparison,
} from './types'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => apiFetch<{ status: string }>('/health'),

  getPipelineStatus: () => apiFetch<PipelineStatus>('/api/pipeline/status'),

  getVelocity: (params?: { company_id?: string; days?: number }) => {
    const q = new URLSearchParams()
    if (params?.company_id) q.set('company_id', params.company_id)
    if (params?.days) q.set('days', String(params.days))
    return apiFetch<DailyVelocity[]>(`/api/aggregation/velocity${q.size ? `?${q}` : ''}`)
  },

  getBrandTimeline: (params?: { brand_id?: string }) => {
    const q = params?.brand_id ? `?brand_id=${params.brand_id}` : ''
    return apiFetch<BrandTimeline[]>(`/api/aggregation/brand-timeline${q}`)
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
  }) => {
    const q = new URLSearchParams()
    if (params?.limit !== undefined) q.set('limit', String(params.limit))
    if (params?.offset !== undefined) q.set('offset', String(params.offset))
    if (params?.company_id) q.set('company_id', params.company_id)
    if (params?.is_active !== undefined) q.set('is_active', String(params.is_active))
    if (params?.role_archetype) q.set('role_archetype', params.role_archetype)
    return apiFetch<PostingListResponse>(`/api/postings${q.size ? `?${q}` : ''}`)
  },

  getPosting: (id: string) => apiFetch<PostingDetail>(`/api/postings/${id}`),

  listEvalRuns: () => apiFetch<EvalRun[]>('/api/eval/runs'),

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

  getEvalLeaderboard: () => apiFetch<Record<string, unknown>>('/api/eval/leaderboard-data'),

  getEloRatings: () => apiFetch<Record<string, number>>('/api/eval/elo'),

  listComparisons: () => apiFetch<EvalComparison[]>('/api/eval/comparisons'),

  createComparison: (body: {
    posting_id: string
    result_a_id: string
    result_b_id: string
    winner: string
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
}
