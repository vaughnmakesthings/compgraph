/**
 * Mock factory for @/api-client/@tanstack/react-query.gen
 *
 * Usage in tests:
 *   vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
 *     const { apiClientRqMock } = await import("./mocks/api-client-rq");
 *     return apiClientRqMock();
 *   });
 *
 * Override specific options in tests:
 *   const mod = await import("@/api-client/@tanstack/react-query.gen");
 *   vi.mocked(mod.getVelocityApiV1AggregationVelocityGetOptions).mockReturnValue({
 *     queryKey: ["velocity"], queryFn: vi.fn().mockResolvedValue(myData),
 *   });
 */

function stubOptions(key: string, defaultData: unknown = {}) {
  return vi.fn(() => ({
    queryKey: [key],
    queryFn: vi.fn().mockResolvedValue(defaultData),
  }));
}

function stubQueryKey(key: string) {
  return vi.fn(() => [key]);
}

function stubMutation() {
  return vi.fn(() => ({
    mutationFn: vi.fn().mockResolvedValue({}),
  }));
}

export function apiClientRqMock(): Record<string, ReturnType<typeof vi.fn>> {
  return {
    // Dashboard / Pipeline
    pipelineStatusApiV1PipelineStatusGetOptions: stubOptions("pipelineStatus", {
      status: "idle",
      scrape: { current_run: null, last_completed_at: null, next_run_at: null },
      enrich: { current_run: null, last_completed_at: null },
      scheduler: { next_run_at: null },
    }),
    healthCheckHealthGetOptions: stubOptions("health", { status: "ok", version: "1.0.0" }),
    pipelineRunsApiV1PipelineRunsGetOptions: stubOptions("pipelineRuns", { scrape_runs: [], enrichment_runs: [] }),

    // Aggregation
    getVelocityApiV1AggregationVelocityGetOptions: stubOptions("velocity", []),
    getCoverageGapsApiV1AggregationCoverageGapsGetOptions: stubOptions("coverageGaps", []),
    triggerAggregationApiV1AggregationTriggerPostMutation: stubMutation(),

    // Scrape
    triggerScrapeApiV1ScrapeTriggerPostMutation: stubMutation(),
    scrapeStatusApiV1ScrapeStatusGetOptions: stubOptions("scrapeStatus", {
      run_id: "", status: "success", started_at: null, finished_at: null,
      total_postings_found: 0, total_snapshots_created: 0, total_errors: 0,
      companies_succeeded: 0, companies_failed: 0, company_states: {}, company_results: {},
    }),
    scrapeStatusApiV1ScrapeStatusGetQueryKey: stubQueryKey("scrapeStatus"),

    // Enrich
    triggerFullApiV1EnrichTriggerPostMutation: stubMutation(),
    enrichStatusApiV1EnrichStatusGetOptions: stubOptions("enrichStatus", {
      run_id: "", status: "success", started_at: null, finished_at: null,
      pass1_result: null, pass2_result: null, total_input_tokens: 0,
      total_output_tokens: 0, total_api_calls: 0, total_dedup_saved: 0,
      circuit_breaker_tripped: false,
    }),

    // Scheduler
    schedulerStatusApiV1SchedulerStatusGetOptions: stubOptions("schedulerStatus", {
      enabled: true, schedules: [], last_pipeline_finished_at: null,
      last_pipeline_success: null, missed_run: false,
    }),
    schedulerStatusApiV1SchedulerStatusGetQueryKey: stubQueryKey("schedulerStatus"),

    // Postings / Companies
    listPostingsApiV1PostingsGetOptions: stubOptions("postings", { items: [], total: 0 }),
    listCompaniesApiV1CompaniesGetOptions: stubOptions("companies", []),

    // Eval
    getRunsApiV1EvalRunsGetOptions: stubOptions("evalRuns", []),
    getRunResultsApiV1EvalRunsRunIdResultsGetOptions: stubOptions("evalRunResults", []),
    getRunResultsApiV1EvalRunsRunIdResultsGetQueryKey: stubQueryKey("evalRunResults"),
    getLeaderboardDataApiV1EvalLeaderboardDataGetOptions: stubOptions("leaderboard", {
      runs: [], elo: {}, comparisons: [], field_accuracy: {},
    }),
    getCorpusApiV1EvalCorpusGetOptions: stubOptions("evalCorpus", []),
    getComparisonsApiV1EvalComparisonsGetOptions: stubOptions("evalComparisons", []),
    getComparisonsApiV1EvalComparisonsGetQueryKey: stubQueryKey("evalComparisons"),
    createComparisonApiV1EvalComparisonsPostMutation: stubMutation(),
    createFieldReviewApiV1EvalFieldReviewsPostMutation: stubMutation(),
    createEvalRunApiV1EvalRunsPostMutation: stubMutation(),
    getModelsApiV1EvalModelsGetOptions: stubOptions("evalModels", []),
    listModelsApiV1EvalModelsGetOptions: stubOptions("evalModels", []),
    getRunsApiV1EvalRunsGetQueryKey: stubQueryKey("evalRuns"),
    createRunApiV1EvalRunsPostMutation: stubMutation(),
    deleteRunApiV1EvalRunsRunIdDeleteMutation: stubMutation(),
  };
}
