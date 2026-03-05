export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface StaticCompany {
  name: string;
  slug: string;
  ats: string;
}

export const COMPANIES: StaticCompany[] = [
  { name: "2020 Companies", slug: "2020", ats: "Workday" },
  { name: "BDS Connected Solutions", slug: "bds", ats: "iCIMS" },
  { name: "MarketSource", slug: "marketsource", ats: "iCIMS" },
  { name: "OSL Retail Services", slug: "osl", ats: "iCIMS" },
  { name: "T-ROC", slug: "troc", ats: "Workday" },
];
