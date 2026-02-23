import { api } from '../lib/api-client'

beforeEach(() => {
  global.fetch = vi.fn()
})

afterEach(() => {
  vi.restoreAllMocks()
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
