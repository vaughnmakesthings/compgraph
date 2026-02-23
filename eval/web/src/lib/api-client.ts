/**
 * Typed API client for the Python eval backend.
 * All pages consume data through this module.
 */

const API_BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

// --- Types (matching Python backend responses) ---

export interface Run {
  id: number;
  created_at: string;
  pass_number: number;
  model: string;
  prompt_version: string;
  corpus_size: number;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  total_cost_usd: number | null;
  total_duration_ms: number | null;
}

export interface Result {
  id: number;
  run_id: number;
  posting_id: string;
  raw_response: string | null;
  parsed_result: string | null; // JSON string
  parse_success: boolean;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface CorpusPosting {
  id: string;
  company_slug: string;
  title: string;
  location: string | null;
  full_text: string;
  reference_pass1: string | null; // JSON string
  reference_pass2: string | null; // JSON string
}

export interface Comparison {
  id: number;
  created_at: string;
  posting_id: string;
  result_a_id: number;
  result_b_id: number;
  winner: "a" | "b" | "tie" | "both_bad";
  notes: string | null;
}

export interface FieldReview {
  id: number;
  created_at: string;
  result_id: number;
  field_name: string;
  model_value: string | null;
  is_correct: number; // 1=correct, 0=wrong, -1=cant-assess
  correct_value: string | null;
}

export interface RunProgress {
  status: "starting" | "running" | "completed" | "failed";
  completed: number;
  total: number;
  run_id?: number;
  succeeded?: number;
  failed?: number;
  cost_usd?: number;
  duration_ms?: number;
  error?: string;
}

// --- Config ---

export async function getModels(): Promise<Record<string, string>> {
  return fetchJSON("/config/models");
}

export async function getPrompts(passNumber: number): Promise<string[]> {
  return fetchJSON(`/config/prompts/${passNumber}`);
}

// --- Runs ---

export async function getRuns(): Promise<Run[]> {
  return fetchJSON("/runs");
}

export async function getRun(id: number): Promise<Run> {
  return fetchJSON(`/runs/${id}`);
}

export async function deleteRun(id: number): Promise<void> {
  await fetchJSON(`/runs/${id}`, { method: "DELETE" });
}

export async function createRun(params: {
  pass_number: number;
  model: string;
  prompt_version: string;
  concurrency?: number;
}): Promise<{ tracking_id: number; status: string; total: number }> {
  return fetchJSON("/runs", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getRunResults(id: number): Promise<Result[]> {
  return fetchJSON(`/runs/${id}/results`);
}

export async function getRunFieldAccuracy(
  id: number,
): Promise<Record<string, number>> {
  return fetchJSON(`/runs/${id}/field-accuracy`);
}

export async function getRunFieldReviews(
  id: number,
): Promise<Record<string, FieldReview[]>> {
  return fetchJSON(`/runs/${id}/field-reviews`);
}

// --- Progress ---

export async function getProgress(trackingId: number): Promise<RunProgress> {
  return fetchJSON(`/progress/${trackingId}`);
}

// --- Corpus ---

export async function getCorpus(): Promise<CorpusPosting[]> {
  return fetchJSON("/corpus");
}

// --- Comparisons ---

export async function getComparisons(): Promise<Comparison[]> {
  return fetchJSON("/comparisons");
}

export async function createComparison(params: {
  posting_id: string;
  result_a_id: number;
  result_b_id: number;
  winner: "a" | "b" | "tie" | "both_bad";
  notes?: string;
}): Promise<{ id: number }> {
  return fetchJSON("/comparisons", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// --- Field Reviews ---

export async function createFieldReview(params: {
  result_id: number;
  field_name: string;
  model_value: string | null;
  is_correct: number;
  correct_value?: string | null;
}): Promise<{ id: number }> {
  return fetchJSON("/field-reviews", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function deleteFieldReview(
  result_id: number,
  field_name: string,
): Promise<void> {
  await fetchJSON<void>(
    `/field-reviews/${result_id}/${encodeURIComponent(field_name)}`,
    { method: "DELETE" },
  );
}

// --- Elo ---

export async function getEloRatings(): Promise<Record<string, number>> {
  return fetchJSON("/elo");
}

// --- Bulk: Leaderboard ---

export interface LeaderboardData {
  runs: Run[];
  elo: Record<string, number>;
  comparisons: Comparison[];
  field_accuracy: Record<string, Record<string, number>>;
  results: Record<string, Result[]>;
}

export async function getLeaderboardData(): Promise<LeaderboardData> {
  return fetchJSON("/leaderboard-data");
}
