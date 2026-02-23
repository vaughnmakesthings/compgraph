export interface PressRelease {
  id: string;
  headline: string;
  date: string; // ISO date
  summary: string;
  source: string;
  category: "product" | "financial" | "partnership" | "leadership" | "marketing";
}

export interface ProspectContact {
  id: string;
  name: string;
  title: string;
  department: string;
  seniority: "c-suite" | "vp" | "director" | "manager";
  relevance: "primary" | "secondary" | "peripheral";
  sources: Array<"apollo" | "linkedin" | "zoominfo">;
  confidence: number; // 0–100
  outreachStatus: "not-contacted" | "in-queue" | "reached-out" | "responded";
  location: string;
}

export interface ProspectSummary {
  name: string;
  slug: string;
  industry: string;
  fieldMarketingSignal: "high" | "medium" | "low";
  hq: string;
  employees: string;
  revenue: string;
}

export interface ProspectMock extends ProspectSummary {
  sector: string;
  description: string;
  narrative: string;
  keyRetailers: string[];
  pressReleases: PressRelease[];
  contacts: ProspectContact[];
  kpis: {
    estimatedFMBudget: string;
    retailDoors: string;
    keyRetailers: string;
    lastSignalDate: string;
  };
}

export const PROSPECTS: ProspectSummary[] = [
  {
    name: "Keurig Dr Pepper",
    slug: "keurig-dr-pepper",
    industry: "Consumer Packaged Goods",
    fieldMarketingSignal: "high",
    hq: "Burlington, MA",
    employees: "~29,000",
    revenue: "$14.8B",
  },
  {
    name: "Weber-Stephen Products",
    slug: "weber",
    industry: "Outdoor & Home",
    fieldMarketingSignal: "medium",
    hq: "Palatine, IL",
    employees: "~5,200",
    revenue: "$1.7B",
  },
  {
    name: "Turtle Beach Corporation",
    slug: "turtle-beach",
    industry: "Consumer Electronics",
    fieldMarketingSignal: "high",
    hq: "San Diego, CA",
    employees: "~580",
    revenue: "$172M",
  },
];

export const PROSPECT_MOCKS: Record<string, ProspectMock> = {
  "keurig-dr-pepper": {
    name: "Keurig Dr Pepper",
    slug: "keurig-dr-pepper",
    industry: "Consumer Packaged Goods",
    sector: "Beverages",
    hq: "Burlington, MA",
    employees: "~29,000",
    revenue: "$14.8B (FY2023)",
    fieldMarketingSignal: "high",
    description:
      "Keurig Dr Pepper is a leading beverage company in North America with a portfolio of more than 125 owned, licensed, and partner brands and distribution across 80,000+ retail doors.",
    narrative:
      "KDP operates one of the most active field marketing programs in the CPG sector, deploying in-store demonstration and sampling events across more than 80,000 retail doors nationally. The company's At-Home division accounts for roughly 47% of net sales and is the primary driver of retail activation spend. Following a Q3 2024 organizational restructuring that elevated channel activation under a new SVP role, the field marketing budget is estimated to have expanded 12–15% year-over-year. KDP's recent national campaign across Walmart — 4,200 stores simultaneously — signals a preference for large-scale, coordinated field execution at a scope that few agencies can deliver without sub-contracting.",
    keyRetailers: ["Walmart", "Target", "Costco", "Kroger", "Sam's Club", "Best Buy", "Amazon"],
    kpis: {
      estimatedFMBudget: "$40–55M",
      retailDoors: "80,000+",
      keyRetailers: "7 major",
      lastSignalDate: "2024-11-14",
    },
    pressReleases: [
      {
        id: "pr-1",
        headline: "Keurig Dr Pepper Appoints Marcus Delgado as SVP, Retail Channel Activation",
        date: "2024-11-14",
        summary:
          "KDP announced the appointment of Marcus Delgado as Senior Vice President, Retail Channel Activation, a newly created executive role reporting directly to the EVP of Sales. Delgado joins from Nestlé USA where he led a $340M field marketing operation across 60+ markets. The role was created following a Q3 strategic review identifying in-store execution consistency as a top-three priority heading into 2025.",
        source: "PR Newswire",
        category: "leadership",
      },
      {
        id: "pr-2",
        headline:
          "KDP Launches 'Brew & Discover' National Demo Campaign Across 4,200 Walmart Locations",
        date: "2024-10-02",
        summary:
          "Keurig Dr Pepper kicked off its largest-ever single-retailer activation campaign in partnership with Walmart, deploying brand ambassadors across all U.S. Walmart Supercenter locations for live Keurig brewing demonstrations. The 12-week campaign is supported by Walmart's in-store digital signage network and expects to generate over 4.2 million consumer touchpoints.",
        source: "Globe Newswire",
        category: "marketing",
      },
      {
        id: "pr-3",
        headline: "Keurig Dr Pepper Reports Q3 2024 Results: At-Home Coffee Net Sales Up 5.1% YoY",
        date: "2024-09-18",
        summary:
          "KDP reported Q3 2024 net sales of $3.89 billion, with the At-Home division growing 5.1% to $1.83 billion. Management raised full-year guidance for At-Home, citing expanded retail door count, new SKU launches, and a strong pipeline of planned retail activation events through Q4.",
        source: "Earnings Release",
        category: "financial",
      },
      {
        id: "pr-4",
        headline:
          "KDP and Costco Expand Partnership with Dedicated Keurig Experience Zones in 312 Warehouses",
        date: "2024-08-05",
        summary:
          "Keurig Dr Pepper and Costco Wholesale formalized a three-year partnership establishing permanent 'Keurig Experience Zones' in 312 U.S. Costco warehouses. Each zone features staffed live demo stations, a curated pod assortment, and a trade-in incentive program. The arrangement includes a first right-of-refusal on new Costco beverage equipment categories through 2027.",
        source: "Business Wire",
        category: "partnership",
      },
      {
        id: "pr-5",
        headline:
          "Keurig Dr Pepper Unveils BOLT24 Sport Hydration Line with Dedicated End-Cap Program at Target and CVS",
        date: "2024-06-23",
        summary:
          "KDP announced the national launch of BOLT24 with a coordinated retail activation program placing 18,000 dedicated end-cap displays at Target and CVS locations simultaneously. Brand ambassador training was completed across six regional hubs, with the field team structure mirroring the successful model used during the 2022 Core Hydration expansion.",
        source: "PR Newswire",
        category: "product",
      },
    ],
    contacts: [
      {
        id: "c-1",
        name: "Marcus Delgado",
        title: "SVP, Retail Channel Activation",
        department: "Sales",
        seniority: "vp",
        relevance: "primary",
        sources: ["apollo", "linkedin"],
        confidence: 91,
        outreachStatus: "not-contacted",
        location: "Boston, MA",
      },
      {
        id: "c-2",
        name: "Jennifer Woo",
        title: "Director, Field Marketing Operations",
        department: "Marketing",
        seniority: "director",
        relevance: "primary",
        sources: ["linkedin"],
        confidence: 84,
        outreachStatus: "reached-out",
        location: "Burlington, MA",
      },
      {
        id: "c-3",
        name: "Brian Callahan",
        title: "VP, Shopper Marketing & In-Store Experience",
        department: "Marketing",
        seniority: "vp",
        relevance: "primary",
        sources: ["apollo"],
        confidence: 88,
        outreachStatus: "not-contacted",
        location: "Burlington, MA",
      },
      {
        id: "c-4",
        name: "Stephanie Okafor",
        title: "Senior Manager, National Accounts — Walmart",
        department: "Sales",
        seniority: "manager",
        relevance: "secondary",
        sources: ["linkedin"],
        confidence: 72,
        outreachStatus: "not-contacted",
        location: "Bentonville, AR",
      },
      {
        id: "c-5",
        name: "David Ferreira",
        title: "Director, Brand Activation & Retail Partnerships",
        department: "Marketing",
        seniority: "director",
        relevance: "primary",
        sources: ["apollo", "linkedin"],
        confidence: 79,
        outreachStatus: "in-queue",
        location: "Burlington, MA",
      },
      {
        id: "c-6",
        name: "Natasha Burke",
        title: "VP, Sales Strategy — At-Home Division",
        department: "Sales",
        seniority: "vp",
        relevance: "secondary",
        sources: ["apollo"],
        confidence: 69,
        outreachStatus: "not-contacted",
        location: "New York, NY",
      },
    ],
  },

  weber: {
    name: "Weber-Stephen Products",
    slug: "weber",
    industry: "Outdoor & Home",
    sector: "Outdoor Cooking",
    hq: "Palatine, IL",
    employees: "~5,200",
    revenue: "$1.7B (FY2023)",
    fieldMarketingSignal: "medium",
    description:
      "Weber-Stephen Products is the world's leading manufacturer of outdoor gas, charcoal, and electric grills with distribution in more than 78 countries.",
    narrative:
      "Weber operates a mid-scale field marketing program concentrated around peak grilling season (April–September), deploying demonstration staff at Home Depot and Lowe's in the top 50 DMAs. The activation budget contracted ~8% in FY2023 following commodity cost pressures but rebounded in Q2 2024 with a renewed focus on live-fire cooking demonstrations. Weber's shift toward premium categories — Genesis and Summit lines — has elevated ROI expectations for in-store demos, creating an opening for agency partners with strong consultative sales methodology. A new CCO appointed in July 2024 is consolidating field operations under a unified commercial structure.",
    keyRetailers: ["Home Depot", "Lowe's", "Ace Hardware", "Walmart", "Target", "Costco"],
    kpis: {
      estimatedFMBudget: "$12–18M",
      retailDoors: "22,000+",
      keyRetailers: "6 major",
      lastSignalDate: "2024-11-01",
    },
    pressReleases: [
      {
        id: "pr-1",
        headline: "Weber Announces 'Fire Up Summer' National Retail Demo Campaign with Home Depot",
        date: "2024-11-01",
        summary:
          "Weber-Stephen Products announced a 14-week spring campaign partnering with The Home Depot to conduct live grilling demonstrations at 1,800 store locations across 42 states. Brand specialists trained on Weber's premium gas and pellet grill lineup will target new homeowner segments, with Weber expecting to reach over 2.8 million consumers during the April–July activation window.",
        source: "Business Wire",
        category: "marketing",
      },
      {
        id: "pr-2",
        headline: "Weber Reports Q3 FY2024: Revenue Up 4.7%, Premium Segment Grows 11.2%",
        date: "2024-10-15",
        summary:
          "Weber-Stephen Products reported fiscal Q3 2024 net revenues of $464 million, up 4.7% year-over-year. The Premium Grills category grew 11.2%, driven by expanded distribution in specialty retail. Management noted a 22% increase in dedicated in-store personnel across Lowe's and Home Depot as a key activation driver.",
        source: "Globe Newswire",
        category: "financial",
      },
      {
        id: "pr-3",
        headline:
          "Weber Expands SmokeFire Line with 'Pit-to-Plate' In-Store Experience Program at 340 Lowe's Locations",
        date: "2024-09-03",
        summary:
          "Weber launched the 'Pit-to-Plate' program to support the SmokeFire pellet grill lineup, with certified Weber grill specialists conducting live smoking and searing demonstrations on weekends at 340 Lowe's locations. The program includes a QR-driven product education hub and an instant rebate for on-site purchases.",
        source: "PR Newswire",
        category: "product",
      },
      {
        id: "pr-4",
        headline: "Weber Appoints Christine Holloway as Chief Commercial Officer",
        date: "2024-07-22",
        summary:
          "Weber-Stephen Products named Christine Holloway as Chief Commercial Officer, consolidating Sales, Marketing, and Customer Experience under a single P&L. Holloway previously served as EVP of Retail Strategy at Spectrum Brands. Her mandate includes closing the gap between online brand investment and in-store conversion rates across Weber's major retail partners.",
        source: "Business Wire",
        category: "leadership",
      },
      {
        id: "pr-5",
        headline:
          "Weber and Ace Hardware Launch 'Backyard Essentials' Co-Branded Program in 3,200 Locations",
        date: "2024-05-14",
        summary:
          "Weber and Ace Hardware announced a co-branded retail program spanning 3,200 independent and company-owned Ace locations, including dedicated Weber endcap fixtures, a certified specialist training program through Ace's dealer network, and seasonal promotional support. The partnership represents Weber's most significant expansion into independent hardware retail in over a decade.",
        source: "PR Newswire",
        category: "partnership",
      },
    ],
    contacts: [
      {
        id: "c-1",
        name: "Christine Holloway",
        title: "Chief Commercial Officer",
        department: "Commercial",
        seniority: "c-suite",
        relevance: "primary",
        sources: ["linkedin"],
        confidence: 87,
        outreachStatus: "not-contacted",
        location: "Chicago, IL",
      },
      {
        id: "c-2",
        name: "Tom Richter",
        title: "VP, Retail Sales & Field Execution",
        department: "Sales",
        seniority: "vp",
        relevance: "primary",
        sources: ["apollo", "linkedin"],
        confidence: 82,
        outreachStatus: "in-queue",
        location: "Palatine, IL",
      },
      {
        id: "c-3",
        name: "Amy Garrison",
        title: "Director, Shopper Marketing",
        department: "Marketing",
        seniority: "director",
        relevance: "primary",
        sources: ["linkedin"],
        confidence: 76,
        outreachStatus: "not-contacted",
        location: "Palatine, IL",
      },
      {
        id: "c-4",
        name: "Kevin Shapiro",
        title: "National Account Director — Home Improvement",
        department: "Sales",
        seniority: "director",
        relevance: "secondary",
        sources: ["apollo"],
        confidence: 68,
        outreachStatus: "not-contacted",
        location: "Atlanta, GA",
      },
    ],
  },

  "turtle-beach": {
    name: "Turtle Beach Corporation",
    slug: "turtle-beach",
    industry: "Consumer Electronics",
    sector: "Gaming Peripherals",
    hq: "San Diego, CA",
    employees: "~580",
    revenue: "$172M (FY2023)",
    fieldMarketingSignal: "high",
    description:
      "Turtle Beach Corporation is the world's leading gaming headset brand and a growing developer of gaming accessories across PC, console, and mobile platforms.",
    narrative:
      "Turtle Beach deploys one of the most concentrated field marketing programs in consumer electronics, with dedicated gaming specialists placed inside GameStop, Best Buy, and Walmart gaming departments during key selling windows (Back-to-School, Black Friday, major franchise launches). The acquisition of PDP in 2023 nearly doubled its retail SKU footprint, dramatically increasing the complexity and scale of in-store execution requirements. Turtle Beach estimates that approximately 60% of gaming accessory sales are influenced by an in-store interaction, making field activation disproportionately important to revenue versus category peers. The company is actively reviewing its field agency partnerships following PDP integration, and the newly appointed VP of Retail Marketing & Field Activation is consolidating programs.",
    keyRetailers: ["GameStop", "Best Buy", "Walmart", "Amazon", "Target", "Costco", "Microsoft Store"],
    kpis: {
      estimatedFMBudget: "$8–14M",
      retailDoors: "8,500+",
      keyRetailers: "7 major",
      lastSignalDate: "2024-11-05",
    },
    pressReleases: [
      {
        id: "pr-1",
        headline:
          "Turtle Beach Launches 'Level Up In-Store' Program with Best Buy Across 1,000 Gaming Specialty Locations",
        date: "2024-11-05",
        summary:
          "Turtle Beach announced its 'Level Up In-Store' activation program with Best Buy, deploying certified gaming specialists at 1,000 locations through the holiday season. Specialists are trained across the full Turtle Beach and PDP portfolio, including the new Stealth Ultra wireless headset, with live demo stations featuring side-by-side competitor comparisons and an in-store trade-up incentive.",
        source: "Business Wire",
        category: "marketing",
      },
      {
        id: "pr-2",
        headline:
          "Turtle Beach Reports Q3 2024 Results: Net Revenue $51.3M, PDP Integration On Track",
        date: "2024-10-30",
        summary:
          "Turtle Beach reported Q3 2024 net revenues of $51.3 million, reflecting the first full quarter of an integrated PDP portfolio. Gross margin expanded 180bps to 28.4%. Management highlighted improved retail sell-through velocity at Walmart and Target, attributed to restructured planogram placement and increased field specialist coverage.",
        source: "Globe Newswire",
        category: "financial",
      },
      {
        id: "pr-3",
        headline:
          "Turtle Beach Appoints Rachel Ng as VP, Retail Marketing & Field Activation",
        date: "2024-09-11",
        summary:
          "Turtle Beach named Rachel Ng as VP, Retail Marketing & Field Activation. Ng joins from Logitech G, where she built and managed a 300-person field team across North American retail. Her mandate includes integrating the Turtle Beach and PDP field programs and establishing a unified retail presence standard across major gaming retail channels.",
        source: "PR Newswire",
        category: "leadership",
      },
      {
        id: "pr-4",
        headline:
          "Turtle Beach and GameStop Expand Partnership to Create Dedicated Gaming Audio Demo Zones in 850 Stores",
        date: "2024-08-19",
        summary:
          "Turtle Beach and GameStop announced dedicated gaming audio demo zones in 850 GameStop locations, featuring live audio comparison capabilities between product tiers. Turtle Beach-trained brand advocates staff zones during peak weekend traffic, with the program designed to increase conversion from browse to purchase on headsets above $100.",
        source: "Business Wire",
        category: "partnership",
      },
      {
        id: "pr-5",
        headline:
          "Turtle Beach Unveils Stealth Ultra at $299 with Nationwide Coordinated Retail Launch",
        date: "2024-07-08",
        summary:
          "Turtle Beach launched the Stealth Ultra flagship wireless headset with simultaneous availability at Best Buy, GameStop, Walmart, and Amazon. The retail launch includes a 90-day in-store activation program with live demonstration events, a pre-order incentive converting to in-store instant rebates, and coordinated digital advertising driving footfall to gaming department locations.",
        source: "PR Newswire",
        category: "product",
      },
    ],
    contacts: [
      {
        id: "c-1",
        name: "Rachel Ng",
        title: "VP, Retail Marketing & Field Activation",
        department: "Marketing",
        seniority: "vp",
        relevance: "primary",
        sources: ["linkedin", "apollo"],
        confidence: 94,
        outreachStatus: "not-contacted",
        location: "San Diego, CA",
      },
      {
        id: "c-2",
        name: "James Kowalski",
        title: "Director, National Accounts — Gaming Retail",
        department: "Sales",
        seniority: "director",
        relevance: "primary",
        sources: ["apollo"],
        confidence: 81,
        outreachStatus: "reached-out",
        location: "San Diego, CA",
      },
      {
        id: "c-3",
        name: "Priya Mehta",
        title: "Senior Manager, Field Operations",
        department: "Marketing",
        seniority: "manager",
        relevance: "primary",
        sources: ["linkedin"],
        confidence: 77,
        outreachStatus: "in-queue",
        location: "Los Angeles, CA",
      },
      {
        id: "c-4",
        name: "Derek Owens",
        title: "VP, Sales Strategy & Channel Management",
        department: "Sales",
        seniority: "vp",
        relevance: "secondary",
        sources: ["apollo", "linkedin"],
        confidence: 73,
        outreachStatus: "not-contacted",
        location: "San Diego, CA",
      },
      {
        id: "c-5",
        name: "Lisa Carmichael",
        title: "National Account Manager — Best Buy",
        department: "Sales",
        seniority: "manager",
        relevance: "secondary",
        sources: ["linkedin"],
        confidence: 65,
        outreachStatus: "responded",
        location: "Minneapolis, MN",
      },
    ],
  },
};
