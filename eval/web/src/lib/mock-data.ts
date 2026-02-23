// Centralized mock data mirroring the eval backend schema.
// All pages consume from here — no inline data arrays in page components.

export type RunStatus = "completed" | "running" | "failed";

export type JudgmentStatus =
  | "correct"
  | "wrong"
  | "improved"
  | "cant-assess"
  | "pending";

export type ComparisonWinner = "a" | "b" | "tie" | "both-bad";

export interface EvalRun {
  id: number;
  model: string;
  prompt: string;
  pass: "pass1" | "pass2";
  status: RunStatus;
  accuracy: string | null;
  cost: string;
  duration: string;
  date: string;
  postings: number;
}

export interface LeaderboardEntry {
  rank: number;
  model: string;
  prompt: string;
  elo: number;
  winRate: string;
  parseRate: string;
  accuracy: string;
  cost: string;
  latency: string;
}

export interface CorpusPosting {
  id: string;
  title: string;
  company: string;
  location: string;
  text: string;
}

export interface FieldReview {
  field: string;
  extracted: string;
  groundTruth: string | null;
  judgment: JudgmentStatus;
}

export interface DiffRow {
  field: string;
  baselineValue: string;
  candidateValue: string;
  baselineCorrect: boolean;
  candidateCorrect: boolean;
}

export interface FieldPopulationRow {
  model: string;
  roleArchetype: string;
  payType: string;
  employmentType: string;
  payMin: string;
  payMax: string;
  clientBrand: string;
}

// ---------------------------------------------------------------------------
// Data arrays
// ---------------------------------------------------------------------------

export const EVAL_RUNS: EvalRun[] = [
  { id: 1, model: "deepseek-v3", prompt: "pass1_v1", pass: "pass1", status: "completed", accuracy: "66.7%", cost: "$0.054", duration: "72s", date: "2026-02-18", postings: 50 },
  { id: 2, model: "gpt-4.1-mini", prompt: "pass1_v1", pass: "pass1", status: "completed", accuracy: "100%", cost: "$0.027", duration: "85s", date: "2026-02-18", postings: 50 },
  { id: 3, model: "haiku-3.5", prompt: "pass1_v1", pass: "pass1", status: "completed", accuracy: null, cost: "$0.191", duration: "236s", date: "2026-02-17", postings: 50 },
  { id: 4, model: "gpt-4o-mini", prompt: "pass1_v1", pass: "pass1", status: "completed", accuracy: null, cost: "$0.027", duration: "94s", date: "2026-02-17", postings: 50 },
  { id: 5, model: "gemini-flash", prompt: "pass1_v1", pass: "pass1", status: "completed", accuracy: null, cost: "$0.033", duration: "118s", date: "2026-02-16", postings: 50 },
  { id: 6, model: "sonnet-4", prompt: "pass2_v1", pass: "pass2", status: "completed", accuracy: null, cost: "$0.310", duration: "184s", date: "2026-02-16", postings: 50 },
];

export const LEADERBOARD: LeaderboardEntry[] = [
  { rank: 1, model: "gpt-4.1-mini", prompt: "pass1_v1", elo: 1580, winRate: "72%", parseRate: "100%", accuracy: "100%", cost: "$0.027", latency: "1.7s" },
  { rank: 2, model: "sonnet-4", prompt: "pass2_v1", elo: 1545, winRate: "64%", parseRate: "98%", accuracy: "—", cost: "$0.310", latency: "3.7s" },
  { rank: 3, model: "deepseek-v3", prompt: "pass1_v1", elo: 1490, winRate: "52%", parseRate: "96%", accuracy: "66.7%", cost: "$0.054", latency: "1.4s" },
  { rank: 4, model: "gemini-flash", prompt: "pass1_v1", elo: 1420, winRate: "38%", parseRate: "94%", accuracy: "—", cost: "$0.033", latency: "2.4s" },
  { rank: 5, model: "gpt-4o-mini", prompt: "pass1_v1", elo: 1385, winRate: "30%", parseRate: "92%", accuracy: "—", cost: "$0.027", latency: "1.9s" },
];

export const FIELD_POPULATION: FieldPopulationRow[] = [
  { model: "gpt-4.1-mini", roleArchetype: "100%", payType: "100%", employmentType: "100%", payMin: "92%", payMax: "88%", clientBrand: "96%" },
  { model: "sonnet-4", roleArchetype: "98%", payType: "100%", employmentType: "98%", payMin: "96%", payMax: "94%", clientBrand: "100%" },
  { model: "deepseek-v3", roleArchetype: "96%", payType: "94%", employmentType: "96%", payMin: "86%", payMax: "82%", clientBrand: "90%" },
  { model: "gemini-flash", roleArchetype: "94%", payType: "92%", employmentType: "94%", payMin: "84%", payMax: "78%", clientBrand: "88%" },
  { model: "gpt-4o-mini", roleArchetype: "92%", payType: "90%", employmentType: "92%", payMin: "80%", payMax: "76%", clientBrand: "86%" },
];

export const CORPUS_POSTINGS: CorpusPosting[] = [
  {
    id: "post-bds-001",
    title: "Brand Ambassador — Samsung Galaxy",
    company: "BDS Connected Solutions",
    location: "Dallas, TX",
    text: "Join our team as a Brand Ambassador representing Samsung Galaxy products in Best Buy locations. $18-22/hr, part-time weekends. Must have retail experience and enthusiasm for consumer electronics.",
  },
  {
    id: "post-ms-001",
    title: "Retail Merchandiser — P&G",
    company: "MarketSource",
    location: "Chicago, IL",
    text: "MarketSource is seeking Retail Merchandisers to support Procter & Gamble product placement across Target stores. $16-19/hr, full-time. Planogram experience preferred.",
  },
  {
    id: "post-troc-001",
    title: "Field Marketing Rep — T-Mobile",
    company: "T-ROC",
    location: "Miami, FL",
    text: "T-ROC is hiring Field Marketing Representatives to drive T-Mobile activations in Walmart locations. $17-21/hr plus commission. Sales experience required.",
  },
];

export const FIELD_REVIEWS: FieldReview[] = [
  { field: "role_archetype", extracted: "brand_ambassador", groundTruth: "brand_ambassador", judgment: "correct" },
  { field: "pay_type", extracted: "hourly", groundTruth: "hourly", judgment: "correct" },
  { field: "employment_type", extracted: "part_time", groundTruth: "part_time", judgment: "correct" },
  { field: "pay_min", extracted: "18.00", groundTruth: "18.00", judgment: "correct" },
  { field: "pay_max", extracted: "24.00", groundTruth: "22.00", judgment: "wrong" },
  { field: "client_brand", extracted: "Samsung", groundTruth: null, judgment: "cant-assess" },
];

// Baseline (deepseek-v3) values match FIELD_REVIEWS extracted values.
// baselineCorrect derived from FIELD_REVIEWS judgments: correct→true, wrong/cant-assess→false.
// Result: 4/6 correct = 66.7% baseline accuracy.
export const DIFF_ROWS: DiffRow[] = [
  { field: "role_archetype", baselineValue: "brand_ambassador", candidateValue: "brand_ambassador", baselineCorrect: true, candidateCorrect: true },
  { field: "pay_type", baselineValue: "hourly", candidateValue: "hourly", baselineCorrect: true, candidateCorrect: true },
  { field: "employment_type", baselineValue: "part_time", candidateValue: "part_time", baselineCorrect: true, candidateCorrect: true },
  { field: "pay_min", baselineValue: "18.00", candidateValue: "18.00", baselineCorrect: true, candidateCorrect: true },
  { field: "pay_max", baselineValue: "24.00", candidateValue: "22.00", baselineCorrect: false, candidateCorrect: true },
  { field: "client_brand", baselineValue: "Samsung", candidateValue: "Samsung", baselineCorrect: false, candidateCorrect: true },
];

// Run B extractions for the review comparison page (gpt-4.1-mini / pass1_v1)
export const RUN_B_EXTRACTIONS = [
  { field: "role_archetype", value: "brand_ambassador" },
  { field: "pay_type", value: "hourly" },
  { field: "employment_type", value: "part_time" },
  { field: "pay_min", value: "18.00" },
  { field: "pay_max", value: "22.00" },
  { field: "client_brand", value: "Samsung" },
];

// Derived constants
export const UNIQUE_MODELS = [...new Set(EVAL_RUNS.map((r) => r.model))];
