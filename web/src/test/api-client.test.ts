import { api } from '../lib/api-client'
import { setAuthToken, resetAuthState } from '../lib/auth-token'
import type { PipelineStatus, EvalResult } from '../lib/types'

vi.mock('../lib/supabase', () => ({
  supabase: { auth: { signOut: vi.fn().mockResolvedValue({ error: null }) } },
}))

beforeEach(() => {
  global.fetch = vi.fn()
  // Mark auth as ready so apiFetch doesn't hang waiting for auth
  setAuthToken(null)
})

afterEach(() => {
  vi.restoreAllMocks()
  resetAuthState()
})

describe('api.getPipelineStatus', () => {
  it('fetches from /api/v1/pipeline/status', async () => {
    const mockStatus: PipelineStatus = {
      status: 'idle',
      scrape: { current_run: null, last_completed_at: null, next_run_at: null },
      enrich: { current_run: null, last_completed_at: null },
      scheduler: { next_run_at: null },
    }
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    } as Response)

    const result = await api.getPipelineStatus()

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toContain('/api/v1/pipeline/status')
    expect(result.status).toBe('idle')
  })
})

describe('api.health', () => {
  it('fetches /health and returns the response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response)

    const result = await api.health()

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.any(Object),
    )
    expect(result.status).toBe('ok')
  })
})

describe('api.listPostings', () => {
  it('builds query params correctly', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], total: 0 }),
    } as Response)

    await api.listPostings({ limit: 10, is_active: true, company_id: 'abc' })

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toContain('limit=10')
    expect(url).toContain('is_active=true')
    expect(url).toContain('company_id=abc')
  })

  it('omits query string when no params provided', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], total: 0 }),
    } as Response)

    await api.listPostings()

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toMatch(/\/api\/v1\/postings$/)
  })
})

describe('api error handling', () => {
  it('throws on non-ok response with status code in message', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
    } as Response)

    await expect(api.getPosting('nonexistent')).rejects.toThrow('API error 404')
  })

  it('throws on 500 server error', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
    } as Response)

    await expect(api.getPipelineStatus()).rejects.toThrow('API error 500')
  })

  it('throws with FastAPI detail when response has detail field', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'No corpus file found' }),
    } as Response)

    await expect(
      api.createEvalRun({
        pass_number: 1,
        model: 'claude-haiku-4-5-20251001',
        prompt_version: 'pass1_v1',
      }),
    ).rejects.toThrow('No corpus file found')
  })
})

describe('api.getVelocity', () => {
  it('appends company_id and days to query string', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response)

    await api.getVelocity({ company_id: 'troc', days: 30 })

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toContain('company_id=troc')
    expect(url).toContain('days=30')
  })

  it('omits query string when no params provided', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response)

    await api.getVelocity()

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toMatch(/\/api\/v1\/aggregation\/velocity$/)
  })
})

describe('api.createEvalRun', () => {
  it('sends POST with JSON body', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ run_id: 'run-1', tracking_id: 42 }),
    } as Response)

    const result = await api.createEvalRun({
      pass_number: 1,
      model: 'claude-haiku-4-5',
      prompt_version: 'v2',
    })

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/eval/runs')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toMatchObject({
      pass_number: 1,
      model: 'claude-haiku-4-5',
      prompt_version: 'v2',
    })
    expect(result.run_id).toBe('run-1')
    expect(result.tracking_id).toBe(42)
  })
})

describe('api.triggerAggregation', () => {
  it('sends POST to /api/v1/aggregation/trigger', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'started' }),
    } as Response)

    const result = await api.triggerAggregation()

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/aggregation/trigger')
    expect(init.method).toBe('POST')
    expect(result.status).toBe('started')
  })
})

describe('api.recordComparison', () => {
  it('sends POST with body to /api/v1/eval/comparisons', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 'comp-123' }),
    } as Response)

    const body = {
      posting_id: 'posting-1',
      result_a_id: 'result-a',
      result_b_id: 'result-b',
      winner: 'a' as const,
      notes: 'A is more accurate',
    }
    const result = await api.recordComparison(body)

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/eval/comparisons')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toMatchObject(body)
    expect(result.id).toBe('comp-123')
  })

  it('works without optional notes field', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 'comp-456' }),
    } as Response)

    await api.recordComparison({
      posting_id: 'posting-2',
      result_a_id: 'result-a',
      result_b_id: 'result-b',
      winner: 'tie',
    })

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    const parsed = JSON.parse(init.body as string)
    expect(parsed.winner).toBe('tie')
    expect(parsed.notes).toBeUndefined()
  })
})

describe('api.getEvalResults', () => {
  it('fetches from /api/v1/eval/runs/{runId}/results', async () => {
    const mockResults: EvalResult[] = [
      {
        id: 'result-1',
        run_id: 'run-abc',
        posting_id: 'posting-1',
        raw_response: '{"role_archetype":"FMR"}',
        parsed_result: { role_archetype: 'FMR' },
        parse_success: true,
        input_tokens: 512,
        output_tokens: 64,
        cost_usd: 0.0012,
        latency_ms: 1200,
        created_at: '2026-02-22T10:00:00Z',
      },
    ]
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResults,
    } as Response)

    const results = await api.getEvalResults('run-abc')

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toContain('/api/v1/eval/runs/run-abc/results')
    expect(results).toHaveLength(1)
    expect(results[0].id).toBe('result-1')
    expect(results[0].parse_success).toBe(true)
  })

  it('returns empty array when run has no results', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response)

    const results = await api.getEvalResults('run-empty')

    expect(results).toHaveLength(0)
  })

  it('throws on 404 when run does not exist', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
    } as Response)

    await expect(api.getEvalResults('run-missing')).rejects.toThrow('API error 404')
  })
})

describe('api.getBrandTimeline', () => {
  it('URL-encodes brand_id containing special characters', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response)

    await api.getBrandTimeline({ brand_id: 'foo&bar' })

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toContain('brand_id=foo%26bar')
    expect(url).not.toContain('brand_id=foo&bar')
  })

  it('omits query string when no brand_id provided', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response)

    await api.getBrandTimeline()

    const url = vi.mocked(fetch).mock.calls[0][0] as string
    expect(url).toMatch(/\/api\/v1\/aggregation\/brand-timeline$/)
  })
})

describe('api network error handling', () => {
  it('wraps fetch TypeError in a normalized network error', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(api.getPipelineStatus()).rejects.toThrow('Network error')
  })
})

describe('api pipeline control endpoints', () => {
  function mockOk(body: unknown) {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => body,
    } as Response)
  }

  it('triggerScrape sends POST to /api/v1/scrape/trigger', async () => {
    mockOk({ run_id: 'run-1', message: 'started' })
    const result = await api.triggerScrape()
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/scrape/trigger')
    expect(init.method).toBe('POST')
    expect(result.run_id).toBe('run-1')
  })

  it('pauseScrape sends POST to /api/v1/scrape/pause', async () => {
    mockOk({ run_id: 'run-1', status: 'PAUSED', message: 'ok' })
    await api.pauseScrape()
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/scrape/pause')
    expect(init.method).toBe('POST')
  })

  it('resumeScrape sends POST to /api/v1/scrape/resume', async () => {
    mockOk({ run_id: 'run-1', status: 'RUNNING', message: 'ok' })
    await api.resumeScrape()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scrape/resume')
  })

  it('stopScrape sends POST to /api/v1/scrape/stop', async () => {
    mockOk({ run_id: 'run-1', status: 'STOPPING', message: 'ok' })
    await api.stopScrape()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scrape/stop')
  })

  it('forceStopScrape sends POST to /api/v1/scrape/force-stop', async () => {
    mockOk({ run_id: 'run-1', status: 'FAILED', message: 'ok' })
    await api.forceStopScrape()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scrape/force-stop')
  })

  it('getScrapeStatus fetches from /api/v1/scrape/status and returns run_id + status', async () => {
    const mockStatus = {
      run_id: 'run-1', status: 'RUNNING', started_at: null, finished_at: null,
      total_postings_found: 10, total_snapshots_created: 5, total_errors: 0,
      companies_succeeded: 2, companies_failed: 0, company_states: {},
    }
    mockOk(mockStatus)
    const result = await api.getScrapeStatus()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scrape/status')
    expect(result.run_id).toBe('run-1')
    expect(result.status).toBe('RUNNING')
  })

  it('triggerEnrichment sends POST to /api/v1/enrich/trigger', async () => {
    mockOk({ run_id: 'enrich-1', message: 'started' })
    const result = await api.triggerEnrichment()
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/enrich/trigger')
    expect(init.method).toBe('POST')
    expect(result.run_id).toBe('enrich-1')
  })

  it('getEnrichStatus fetches from /api/v1/enrich/status', async () => {
    const mockStatus = {
      run_id: 'enrich-1', status: 'running', started_at: null, finished_at: null,
      pass1_result: { succeeded: 50, failed: 0, skipped: 0 },
      pass2_result: { succeeded: 45, failed: 0, skipped: 5 },
      total_input_tokens: 10000, total_output_tokens: 2000,
      total_api_calls: 50, total_dedup_saved: 5, circuit_breaker_tripped: false,
    }
    mockOk(mockStatus)
    const result = await api.getEnrichStatus()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/enrich/status')
    expect(result.run_id).toBe('enrich-1')
    expect(result.circuit_breaker_tripped).toBe(false)
  })

  it('getSchedulerStatus fetches from /api/v1/scheduler/status', async () => {
    const mockStatus = {
      enabled: true, schedules: [], last_pipeline_finished_at: null,
      last_pipeline_success: null, missed_run: false,
    }
    mockOk(mockStatus)
    const result = await api.getSchedulerStatus()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scheduler/status')
    expect(result.enabled).toBe(true)
    expect(result.missed_run).toBe(false)
  })

  it('triggerSchedulerJob sends POST with jobId in URL', async () => {
    mockOk({ job_id: 'daily_pipeline', message: 'triggered' })
    const result = await api.triggerSchedulerJob('daily_pipeline')
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/scheduler/jobs/daily_pipeline/trigger')
    expect(init.method).toBe('POST')
    expect(result.job_id).toBe('daily_pipeline')
  })

  it('pauseSchedulerJob sends POST and returns paused: true', async () => {
    mockOk({ schedule_id: 'daily_pipeline', paused: true, message: 'ok' })
    const result = await api.pauseSchedulerJob('daily_pipeline')
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scheduler/jobs/daily_pipeline/pause')
    expect(result.paused).toBe(true)
  })

  it('resumeSchedulerJob sends POST and returns paused: false', async () => {
    mockOk({ schedule_id: 'daily_pipeline', paused: false, message: 'ok' })
    const result = await api.resumeSchedulerJob('daily_pipeline')
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/scheduler/jobs/daily_pipeline/resume')
    expect(result.paused).toBe(false)
  })
})

describe('api simple GET endpoints', () => {
  it('api.getPayBenchmarks fetches /api/v1/aggregation/pay-benchmarks', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => [] } as Response)
    await api.getPayBenchmarks()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/aggregation/pay-benchmarks')
  })

  it('api.getChurnSignals fetches /api/v1/aggregation/churn-signals', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => [] } as Response)
    await api.getChurnSignals()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/aggregation/churn-signals')
  })

  it('api.getEvalModels fetches /api/v1/eval/models', async () => {
    const mockModels = [
      { id: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5 (fast, cheap)' },
    ]
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockModels,
    } as Response)
    const result = await api.getEvalModels()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/eval/models')
    expect(result).toEqual(mockModels)
  })

  it('api.listEvalRuns fetches /api/v1/eval/runs', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => [] } as Response)
    await api.listEvalRuns()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/eval/runs')
  })

  it('api.getEvalLeaderboard fetches /api/v1/eval/leaderboard-data', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ runs: [], elo: {}, comparisons: [], field_accuracy: {} }),
    } as Response)
    const result = await api.getEvalLeaderboard()
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain('/api/v1/eval/leaderboard-data')
    expect(result.runs).toEqual([])
  })

  it('api.upsertFieldReview sends POST to /api/v1/eval/field-reviews', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'fr-1' }) } as Response)
    const result = await api.upsertFieldReview({ result_id: 'r1', field_name: 'role_archetype', is_correct: 1 })
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/eval/field-reviews')
    expect(init.method).toBe('POST')
    expect(result.id).toBe('fr-1')
  })
})

describe('auth token injection', () => {
  it('includes Authorization header when token is set', async () => {
    setAuthToken('test-jwt-token')
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response)

    await api.health()

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer test-jwt-token')
  })

  it('omits Authorization header when no token is set', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response)

    await api.health()

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('does not call signOut on 401 response', async () => {
    const { supabase } = await import('../lib/supabase')
    setAuthToken('expired-token')
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
    } as Response)

    await expect(api.health()).rejects.toThrow('API error 401')
    expect(supabase?.auth.signOut).not.toHaveBeenCalled()
  })

  it('redirects to /login on 401 when auth is ready', async () => {
    const originalLocation = window.location
    const assignMock = vi.fn()
    const locationProxy = { ...originalLocation }
    Object.defineProperty(locationProxy, 'href', {
      get: () => originalLocation.href,
      set: assignMock,
    })
    Object.defineProperty(window, 'location', {
      writable: true,
      value: locationProxy,
    })

    setAuthToken('expired-token')
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
    } as Response)

    await expect(api.health()).rejects.toThrow('API error 401')
    expect(assignMock).toHaveBeenCalledWith('/login')

    Object.defineProperty(window, 'location', { writable: true, value: originalLocation })
  })

  it('waits for auth to be ready before making requests', async () => {
    resetAuthState()

    let fetchCalled = false
    vi.mocked(fetch).mockImplementation(async () => {
      fetchCalled = true
      return { ok: true, json: async () => ({ status: 'ok' }) } as Response
    })

    const promise = api.health()

    // Fetch should not have been called yet — auth is not ready
    await new Promise((r) => setTimeout(r, 10))
    expect(fetchCalled).toBe(false)

    // Mark auth as ready
    setAuthToken('late-token')

    await promise
    expect(fetchCalled).toBe(true)

    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer late-token')
  })
})

describe('api.inviteUser', () => {
  it('sends POST to /api/v1/admin/invite', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ user_id: 'u-123', email: 'new@co.com', role: 'user' }),
    } as Response)

    const result = await api.inviteUser({ email: 'new@co.com', role: 'user' })

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/admin/invite')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ email: 'new@co.com', role: 'user' })
    expect(result.user_id).toBe('u-123')
  })
})
