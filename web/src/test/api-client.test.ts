import { api } from '../lib/api-client'
import type { PipelineStatus, EvalResult } from '../lib/types'

beforeEach(() => {
  global.fetch = vi.fn()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api.getPipelineStatus', () => {
  it('fetches from /api/pipeline/status', async () => {
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
    expect(url).toContain('/api/pipeline/status')
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
    expect(url).toMatch(/\/api\/postings$/)
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
    expect(url).toMatch(/\/api\/aggregation\/velocity$/)
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
    expect(url).toContain('/api/eval/runs')
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
  it('sends POST to /api/aggregation/trigger', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'started' }),
    } as Response)

    const result = await api.triggerAggregation()

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/aggregation/trigger')
    expect(init.method).toBe('POST')
    expect(result.status).toBe('started')
  })
})

describe('api.recordComparison', () => {
  it('sends POST with body to /api/eval/comparisons', async () => {
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
    expect(url).toContain('/api/eval/comparisons')
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
  it('fetches from /api/eval/runs/{runId}/results', async () => {
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
    expect(url).toContain('/api/eval/runs/run-abc/results')
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
    expect(url).toMatch(/\/api\/aggregation\/brand-timeline$/)
  })
})

describe('api network error handling', () => {
  it('wraps fetch TypeError in a normalized network error', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(api.getPipelineStatus()).rejects.toThrow('Network error')
  })
})
