export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface Company {
  name: string;
  slug: string;
  ats: string;
}

export const COMPANIES: Company[] = [
  { name: "Advantage Solutions", slug: "advantage", ats: "Workday" },
  { name: "Acosta Group", slug: "acosta", ats: "Workday" },
  { name: "BDS Connected Solutions", slug: "bds", ats: "iCIMS" },
  { name: "MarketSource", slug: "marketsource", ats: "iCIMS" },
  { name: "T-ROC", slug: "troc", ats: "Workday" },
];
