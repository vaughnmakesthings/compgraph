export interface GlassdoorReview {
  id: string
  rating: number
  date: string
  title: string
  role: string
  employmentStatus: string
  location: string
  recommend: boolean | null
  ceoApproval: boolean | null
  businessOutlook: boolean | null
  pros: string
  cons: string
}

export interface DossierMock {
  slug: string
  hq: string
  clientBrands: string[]
  operatingIn: string[]
  totalRolesFound: number
  rolesClosed: number
  kpis: {
    activePostings: number
    newThisWeek: number
    avgPayMin: number | null
    topRole: string
    trend: { direction: "up" | "down" | "flat"; pct: string } | null
  }
  insight: string
  narrative: string
  roleDistribution: Array<{ role: string; count: number }>
  geographicFocus: string
  payBenchmarks: Array<{
    role_archetype: string
    pay_min_avg: number | null
    pay_max_avg: number | null
  }>
  topBrands: Array<{ brand_name: string; count: number }>
  dataNote: string
  postings: Array<{
    id: string
    title: string
    location: string
    role_archetype: string
    is_active: boolean
    first_seen_at: string
  }>
  glassdoor: {
    overallRating: number
    totalReviews: number
    recommendPct: number
    ceoName: string
    ceoApprovalPct: number
    businessOutlookPct: number
    interviewPositivePct: number
    interviewDifficulty: number
    interviewReviewCount: number
    ratingsByCategory: Array<{
      label: string
      score: number
      trend: "up" | "down" | "flat"
    }>
    reviews: GlassdoorReview[]
  }
}

export const DOSSIER_MOCKS: Record<string, DossierMock> = {
  troc: {
    slug: "troc",
    hq: "Doral, FL",
    clientBrands: ["Samsung", "Apple", "Verizon", "T-Mobile", "Spectrum"],
    operatingIn: ["Best Buy", "Carrier stores", "Big-box retail"],
    totalRolesFound: 312,
    rolesClosed: 223,
    kpis: {
      activePostings: 89,
      newThisWeek: 12,
      avgPayMin: 48000,
      topRole: "FMR",
      trend: { direction: "up", pct: "+16%" },
    },
    insight:
      "T-ROC is doubling down on Samsung-branded Field Marketing Reps in Southeast retail corridors, with 67% of new postings concentrated in FL, TX, and GA.",
    narrative:
      "T-ROC is a premier retail services company specializing in outsourced field sales and brand representation across consumer electronics. Their national footprint spans major carriers and CE brands, with particular depth in Samsung activations. Recent expansion signals a push to dominate Southeast corridor store counts before the summer device cycle.",
    roleDistribution: [
      { role: "FMR", count: 41 },
      { role: "Brand Ambassador", count: 28 },
      { role: "Retail Sales", count: 12 },
      { role: "Area Manager", count: 8 },
    ],
    geographicFocus:
      "Florida, Texas, Georgia — Southeast corridor dominance with ~67% of open headcount in these three states.",
    payBenchmarks: [
      { role_archetype: "FMR", pay_min_avg: 44000, pay_max_avg: 54000 },
      { role_archetype: "Brand Ambassador", pay_min_avg: 38000, pay_max_avg: 46000 },
      { role_archetype: "Area Manager", pay_min_avg: 62000, pay_max_avg: 78000 },
    ],
    topBrands: [
      { brand_name: "Samsung", count: 41 },
      { brand_name: "Verizon", count: 18 },
      { brand_name: "T-Mobile", count: 14 },
      { brand_name: "Apple", count: 9 },
      { brand_name: "Spectrum", count: 6 },
    ],
    dataNote:
      "Posting counts reflect the most recent 30-day scrape window. Some postings may represent re-fills of the same position rather than net-new headcount.",
    postings: [
      {
        id: "troc-1",
        title: "Field Marketing Representative – Samsung",
        location: "Orlando, FL",
        role_archetype: "FMR",
        is_active: true,
        first_seen_at: "2026-02-10T00:00:00Z",
      },
      {
        id: "troc-2",
        title: "Field Marketing Representative – Samsung",
        location: "Miami, FL",
        role_archetype: "FMR",
        is_active: true,
        first_seen_at: "2026-02-08T00:00:00Z",
      },
      {
        id: "troc-3",
        title: "Brand Ambassador – Verizon",
        location: "Dallas, TX",
        role_archetype: "Brand Ambassador",
        is_active: true,
        first_seen_at: "2026-02-12T00:00:00Z",
      },
      {
        id: "troc-4",
        title: "Retail Sales Specialist",
        location: "Atlanta, GA",
        role_archetype: "Retail Sales",
        is_active: false,
        first_seen_at: "2026-01-25T00:00:00Z",
      },
      {
        id: "troc-5",
        title: "Area Manager – Southeast",
        location: "Tampa, FL",
        role_archetype: "Area Manager",
        is_active: true,
        first_seen_at: "2026-02-15T00:00:00Z",
      },
    ],
    glassdoor: {
      overallRating: 3.9,
      totalReviews: 938,
      recommendPct: 72,
      ceoName: "Brett Beveridge",
      ceoApprovalPct: 79,
      businessOutlookPct: 68,
      interviewPositivePct: 50,
      interviewDifficulty: 2.9,
      interviewReviewCount: 69,
      ratingsByCategory: [
        { label: "Diversity & inclusion", score: 4.2, trend: "up" },
        { label: "Work/Life balance", score: 4.0, trend: "up" },
        { label: "Culture & values", score: 3.9, trend: "flat" },
        { label: "Compensation & benefits", score: 3.8, trend: "up" },
        { label: "Career opportunities", score: 3.8, trend: "up" },
        { label: "Senior management", score: 3.7, trend: "flat" },
      ],
      reviews: [
        {
          id: "troc-r1",
          rating: 2.0,
          date: "Feb 5, 2026",
          title: "Low Pay, High Standards",
          role: "Sales Lead",
          employmentStatus: "Current employee, >1 year",
          location: "Vero Beach, FL",
          recommend: false,
          ceoApproval: false,
          businessOutlook: null,
          pros: "Wireless discounts, sales bonuses, autonomy running my own team.",
          cons: "Terrible atmosphere. Standards placed on stores are unrealistic — it isn't a motivation issue, it's a systemic expectation problem.",
        },
        {
          id: "troc-r2",
          rating: 5.0,
          date: "Oct 21, 2025",
          title: "Great place to work and grow",
          role: "Engagement Coordinator",
          employmentStatus: "Current employee, <1 year",
          location: "Guatemala City",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Supportive team, clear communication, great culture, and real learning opportunities.",
          cons: "Sometimes busy days, but overall a very manageable workload.",
        },
        {
          id: "troc-r3",
          rating: 3.0,
          date: "Jan 14, 2026",
          title: "Solid opportunity, but execution varies by region",
          role: "Field Marketing Representative",
          employmentStatus: "Former employee, 2–3 years",
          location: "Tampa, FL",
          recommend: true,
          ceoApproval: null,
          businessOutlook: false,
          pros: "Good brand training, Samsung account is well-managed, pay is competitive for the market.",
          cons: "Regional management quality is inconsistent. Southeast territories feel overworked heading into Q4.",
        },
        {
          id: "troc-r4",
          rating: 4.0,
          date: "Dec 2, 2025",
          title: "Good if you thrive in retail pace",
          role: "Brand Ambassador",
          employmentStatus: "Current employee, 1–2 years",
          location: "Houston, TX",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Fast-paced, excellent product knowledge training, commissions are real and achievable.",
          cons: "Benefits package is thin. Health coverage options need serious improvement.",
        },
      ],
    },
  },

  bds: {
    slug: "bds",
    hq: "Fort Lauderdale, FL",
    clientBrands: ["HP", "Google", "Canon", "Lenovo", "LG"],
    operatingIn: ["Best Buy", "Walmart", "Costco"],
    totalRolesFound: 187,
    rolesClosed: 125,
    kpis: {
      activePostings: 62,
      newThisWeek: 5,
      avgPayMin: 42000,
      topRole: "Demo Specialist",
      trend: { direction: "flat", pct: "+3%" },
    },
    insight:
      "BDS is expanding its in-store demo presence with HP and Google, targeting Midwest big-box locations showing strong Q1 foot traffic.",
    narrative:
      "BDS Connected Solutions operates premium in-store merchandising and live demo programs across consumer electronics and home appliances. Their strength is in building brand experience at retail — placing trained specialists inside Best Buy and Walmart locations to drive attach rates. Q1 expansion into HP and Google programs suggests increased vendor investment in experiential retail.",
    roleDistribution: [
      { role: "Demo Specialist", count: 29 },
      { role: "Merchandiser", count: 18 },
      { role: "Product Educator", count: 11 },
      { role: "Retail Sales", count: 4 },
    ],
    geographicFocus:
      "Illinois, Ohio, Michigan — strong Midwest concentration anchored around Chicago and Detroit metro areas.",
    payBenchmarks: [
      { role_archetype: "Demo Specialist", pay_min_avg: 38000, pay_max_avg: 48000 },
      { role_archetype: "Merchandiser", pay_min_avg: 34000, pay_max_avg: 42000 },
      { role_archetype: "Product Educator", pay_min_avg: 40000, pay_max_avg: 50000 },
    ],
    topBrands: [
      { brand_name: "HP", count: 29 },
      { brand_name: "Google", count: 22 },
      { brand_name: "Canon", count: 16 },
      { brand_name: "Lenovo", count: 12 },
      { brand_name: "LG", count: 8 },
    ],
    dataNote:
      "BDS postings frequently omit pay data in iCIMS listings. Pay benchmarks are derived from the ~45% of postings that include compensation ranges.",
    postings: [
      {
        id: "bds-1",
        title: "Demo Specialist – HP",
        location: "Chicago, IL",
        role_archetype: "Demo Specialist",
        is_active: true,
        first_seen_at: "2026-02-11T00:00:00Z",
      },
      {
        id: "bds-2",
        title: "Demo Specialist – Google",
        location: "Columbus, OH",
        role_archetype: "Demo Specialist",
        is_active: true,
        first_seen_at: "2026-02-09T00:00:00Z",
      },
      {
        id: "bds-3",
        title: "In-Store Merchandiser",
        location: "Detroit, MI",
        role_archetype: "Merchandiser",
        is_active: true,
        first_seen_at: "2026-02-07T00:00:00Z",
      },
      {
        id: "bds-4",
        title: "Product Educator – Canon",
        location: "Indianapolis, IN",
        role_archetype: "Product Educator",
        is_active: false,
        first_seen_at: "2026-01-20T00:00:00Z",
      },
    ],
    glassdoor: {
      overallRating: 3.4,
      totalReviews: 189,
      recommendPct: 62,
      ceoName: "Jason Rosica",
      ceoApprovalPct: 67,
      businessOutlookPct: 55,
      interviewPositivePct: 45,
      interviewDifficulty: 2.6,
      interviewReviewCount: 41,
      ratingsByCategory: [
        { label: "Diversity & inclusion", score: 3.8, trend: "flat" },
        { label: "Work/Life balance", score: 3.6, trend: "up" },
        { label: "Culture & values", score: 3.4, trend: "flat" },
        { label: "Compensation & benefits", score: 3.1, trend: "down" },
        { label: "Career opportunities", score: 3.3, trend: "up" },
        { label: "Senior management", score: 3.2, trend: "flat" },
      ],
      reviews: [
        {
          id: "bds-r1",
          rating: 4.0,
          date: "Jan 22, 2026",
          title: "Strong demos program, weak internal comms",
          role: "Demo Specialist",
          employmentStatus: "Current employee, 1–2 years",
          location: "Chicago, IL",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "HP and Google programs are well-funded. Lots of product to demo, good retail visibility.",
          cons: "Internal communication from corporate is scattered. You often hear about program changes from the client before BDS tells you.",
        },
        {
          id: "bds-r2",
          rating: 2.0,
          date: "Dec 18, 2025",
          title: "Pay hasn't kept up with cost of living",
          role: "Merchandiser",
          employmentStatus: "Former employee, 3–5 years",
          location: "Detroit, MI",
          recommend: false,
          ceoApproval: false,
          businessOutlook: false,
          pros: "Flexible schedule, easy to get along with store staff.",
          cons: "Pay has barely moved in three years while expectations increased. No clear promotion path for merchandisers.",
        },
        {
          id: "bds-r3",
          rating: 4.0,
          date: "Nov 30, 2025",
          title: "Great for product enthusiasts",
          role: "Product Educator",
          employmentStatus: "Current employee, <1 year",
          location: "Columbus, OH",
          recommend: true,
          ceoApproval: null,
          businessOutlook: true,
          pros: "Hands-on time with cutting-edge tech. Canon and Lenovo reps are invested in your success.",
          cons: "Onboarding is rushed. Would benefit from a longer ramp-up period before hitting the floor.",
        },
        {
          id: "bds-r4",
          rating: 3.0,
          date: "Oct 8, 2025",
          title: "Middle of the road",
          role: "Retail Sales Associate",
          employmentStatus: "Current employee, 1–2 years",
          location: "Indianapolis, IN",
          recommend: true,
          ceoApproval: null,
          businessOutlook: null,
          pros: "Steady hours, good coworkers, decent brand exposure.",
          cons: "Management visibility is low. Decisions feel made far away from the field.",
        },
      ],
    },
  },

  marketsource: {
    slug: "marketsource",
    hq: "Alpharetta, GA",
    clientBrands: ["AT&T", "Verizon", "T-Mobile", "Samsung", "Apple"],
    operatingIn: ["AT&T stores", "Verizon stores", "T-Mobile stores", "Carrier retail"],
    totalRolesFound: 445,
    rolesClosed: 321,
    kpis: {
      activePostings: 124,
      newThisWeek: 18,
      avgPayMin: 52000,
      topRole: "Retail Sales",
      trend: { direction: "up", pct: "+17%" },
    },
    insight:
      "MarketSource is the most active competitor this week, aggressively staffing carrier retail ahead of a predicted summer device upgrade cycle.",
    narrative:
      "MarketSource is a large-scale outsourced sales organization with deep carrier retail expertise, operating across AT&T, Verizon, and T-Mobile channels. Their scale — nearly double the active posting count of most competitors — reflects their position as the dominant outsourced staffing partner for wireless carriers. The aggressive week-over-week surge suggests coordinated national hiring ahead of a spring/summer device cycle.",
    roleDistribution: [
      { role: "Retail Sales", count: 58 },
      { role: "Sales Manager", count: 32 },
      { role: "Area Director", count: 22 },
      { role: "Brand Ambassador", count: 12 },
    ],
    geographicFocus:
      "Arizona, California, Texas — Southwest and West Coast focus aligned with high-density carrier retail markets.",
    payBenchmarks: [
      { role_archetype: "Retail Sales", pay_min_avg: 46000, pay_max_avg: 58000 },
      { role_archetype: "Sales Manager", pay_min_avg: 58000, pay_max_avg: 72000 },
      { role_archetype: "Area Director", pay_min_avg: 74000, pay_max_avg: 92000 },
    ],
    topBrands: [
      { brand_name: "AT&T", count: 58 },
      { brand_name: "Verizon", count: 44 },
      { brand_name: "T-Mobile", count: 32 },
      { brand_name: "Samsung", count: 21 },
      { brand_name: "Apple", count: 9 },
    ],
    dataNote:
      "MarketSource's high posting volume may include both direct-hire and vendor-managed listings. Active count reflects unique external job IDs only.",
    postings: [
      {
        id: "ms-1",
        title: "Retail Sales Consultant – AT&T",
        location: "Phoenix, AZ",
        role_archetype: "Retail Sales",
        is_active: true,
        first_seen_at: "2026-02-14T00:00:00Z",
      },
      {
        id: "ms-2",
        title: "Retail Sales Consultant – Verizon",
        location: "Los Angeles, CA",
        role_archetype: "Retail Sales",
        is_active: true,
        first_seen_at: "2026-02-13T00:00:00Z",
      },
      {
        id: "ms-3",
        title: "Sales Manager – T-Mobile",
        location: "Austin, TX",
        role_archetype: "Sales Manager",
        is_active: true,
        first_seen_at: "2026-02-10T00:00:00Z",
      },
      {
        id: "ms-4",
        title: "Area Director – Southwest",
        location: "Scottsdale, AZ",
        role_archetype: "Area Director",
        is_active: true,
        first_seen_at: "2026-02-08T00:00:00Z",
      },
      {
        id: "ms-5",
        title: "Brand Ambassador – Samsung",
        location: "San Diego, CA",
        role_archetype: "Brand Ambassador",
        is_active: false,
        first_seen_at: "2026-01-28T00:00:00Z",
      },
    ],
    glassdoor: {
      overallRating: 3.7,
      totalReviews: 412,
      recommendPct: 68,
      ceoName: "David Habiger",
      ceoApprovalPct: 74,
      businessOutlookPct: 62,
      interviewPositivePct: 58,
      interviewDifficulty: 3.1,
      interviewReviewCount: 87,
      ratingsByCategory: [
        { label: "Diversity & inclusion", score: 4.0, trend: "up" },
        { label: "Work/Life balance", score: 3.8, trend: "flat" },
        { label: "Culture & values", score: 3.7, trend: "up" },
        { label: "Compensation & benefits", score: 3.5, trend: "up" },
        { label: "Career opportunities", score: 3.9, trend: "up" },
        { label: "Senior management", score: 3.5, trend: "flat" },
      ],
      reviews: [
        {
          id: "ms-r1",
          rating: 5.0,
          date: "Feb 10, 2026",
          title: "Best-in-class carrier sales training",
          role: "Retail Sales Consultant",
          employmentStatus: "Current employee, 2–3 years",
          location: "Phoenix, AZ",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "AT&T program is phenomenal — structured training, clear metrics, real earning potential. Management knows the carrier business inside and out.",
          cons: "High turnover in competitive markets makes team continuity hard.",
        },
        {
          id: "ms-r2",
          rating: 3.0,
          date: "Jan 5, 2026",
          title: "Scale creates blind spots",
          role: "Sales Manager",
          employmentStatus: "Current employee, 1–2 years",
          location: "Los Angeles, CA",
          recommend: true,
          ceoApproval: null,
          businessOutlook: true,
          pros: "Company size means stability and real career ladders. Lots of internal mobility across carriers.",
          cons: "At this scale, individual stores can feel like afterthoughts. Process-heavy and slow to adapt.",
        },
        {
          id: "ms-r3",
          rating: 2.0,
          date: "Dec 14, 2025",
          title: "Overworked, under-recognized",
          role: "Brand Ambassador",
          employmentStatus: "Former employee, <1 year",
          location: "Austin, TX",
          recommend: false,
          ceoApproval: false,
          businessOutlook: false,
          pros: "Good for learning the wireless industry quickly.",
          cons: "Quotas are aggressive and reset monthly with no grace period. T-Mobile program had unrealistic attach targets.",
        },
        {
          id: "ms-r4",
          rating: 4.0,
          date: "Nov 20, 2025",
          title: "Solid platform for a carrier career",
          role: "Area Director",
          employmentStatus: "Current employee, 3–5 years",
          location: "Scottsdale, AZ",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Multi-carrier exposure is unmatched. Verizon and AT&T experience gives you credibility anywhere in the industry.",
          cons: "Director bandwidth is stretched thin. Would benefit from more regional support layers.",
        },
      ],
    },
  },

  osl: {
    slug: "osl",
    hq: "Mississauga, ON",
    clientBrands: ["Samsung", "LG", "Sony"],
    operatingIn: ["Walmart", "Best Buy", "Costco"],
    totalRolesFound: 98,
    rolesClosed: 64,
    kpis: {
      activePostings: 34,
      newThisWeek: 2,
      avgPayMin: 38000,
      topRole: "Sales Associate",
      trend: { direction: "flat", pct: "+6%" },
    },
    insight:
      "OSL Retail Services has a modest posting footprint but shows unusual concentration in Walmart and Best Buy channel partnerships — a high brand loyalty signal.",
    narrative:
      "OSL Retail Services focuses on big-box channel optimization, placing sales specialists inside Walmart and Best Buy locations to represent consumer electronics brands. Their smaller posting volume reflects a more selective, relationship-driven staffing model compared to higher-volume competitors. The Samsung and big-box retailer brand concentration suggests deep account relationships with a handful of strategic partners.",
    roleDistribution: [
      { role: "Sales Associate", count: 18 },
      { role: "Territory Manager", count: 10 },
      { role: "Retail Specialist", count: 6 },
    ],
    geographicFocus:
      "Florida and Southeast — geographic overlap with T-ROC signals potential market share competition in the same retail corridors.",
    payBenchmarks: [
      { role_archetype: "Sales Associate", pay_min_avg: 34000, pay_max_avg: 44000 },
      { role_archetype: "Territory Manager", pay_min_avg: 48000, pay_max_avg: 60000 },
    ],
    topBrands: [
      { brand_name: "Samsung", count: 18 },
      { brand_name: "Walmart", count: 12 },
      { brand_name: "Best Buy", count: 10 },
      { brand_name: "Costco", count: 6 },
    ],
    dataNote:
      "OSL's low posting count makes week-over-week trend analysis less reliable. Small sample sizes can exaggerate percentage swings.",
    postings: [
      {
        id: "osl-1",
        title: "Samsung Sales Associate – Walmart",
        location: "Jacksonville, FL",
        role_archetype: "Sales Associate",
        is_active: true,
        first_seen_at: "2026-02-13T00:00:00Z",
      },
      {
        id: "osl-2",
        title: "Samsung Sales Specialist – Best Buy",
        location: "Charlotte, NC",
        role_archetype: "Sales Associate",
        is_active: true,
        first_seen_at: "2026-02-11T00:00:00Z",
      },
      {
        id: "osl-3",
        title: "Territory Manager – Southeast",
        location: "Orlando, FL",
        role_archetype: "Territory Manager",
        is_active: true,
        first_seen_at: "2026-02-06T00:00:00Z",
      },
      {
        id: "osl-4",
        title: "Retail Specialist – Costco",
        location: "Tampa, FL",
        role_archetype: "Retail Specialist",
        is_active: false,
        first_seen_at: "2026-01-30T00:00:00Z",
      },
    ],
    glassdoor: {
      overallRating: 3.5,
      totalReviews: 156,
      recommendPct: 60,
      ceoName: "Greg McDonald",
      ceoApprovalPct: 68,
      businessOutlookPct: 51,
      interviewPositivePct: 47,
      interviewDifficulty: 2.7,
      interviewReviewCount: 38,
      ratingsByCategory: [
        { label: "Diversity & inclusion", score: 3.7, trend: "flat" },
        { label: "Work/Life balance", score: 3.9, trend: "up" },
        { label: "Culture & values", score: 3.5, trend: "flat" },
        { label: "Compensation & benefits", score: 3.0, trend: "down" },
        { label: "Career opportunities", score: 3.2, trend: "flat" },
        { label: "Senior management", score: 3.3, trend: "flat" },
      ],
      reviews: [
        {
          id: "osl-r1",
          rating: 4.0,
          date: "Feb 1, 2026",
          title: "Steady work, great for the Walmart channel",
          role: "Sales Associate",
          employmentStatus: "Current employee, 2–3 years",
          location: "Jacksonville, FL",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Long-standing Walmart relationship gives the work real stability. Samsung program is well-run and consistent.",
          cons: "Growth is limited unless you move to territory manager, and those roles rarely open up.",
        },
        {
          id: "osl-r2",
          rating: 2.0,
          date: "Jan 10, 2026",
          title: "Compensation hasn't kept pace",
          role: "Retail Specialist",
          employmentStatus: "Former employee, 1–2 years",
          location: "Tampa, FL",
          recommend: false,
          ceoApproval: null,
          businessOutlook: false,
          pros: "Flexible hours, independent work style, low-pressure day-to-day.",
          cons: "Pay is the lowest in the market for comparable roles. Benefits are minimal with no clear path upward.",
        },
        {
          id: "osl-r3",
          rating: 4.0,
          date: "Dec 20, 2025",
          title: "Best Buy accounts are well-run",
          role: "Territory Manager",
          employmentStatus: "Current employee, 3–5 years",
          location: "Orlando, FL",
          recommend: true,
          ceoApproval: true,
          businessOutlook: null,
          pros: "Best Buy account management is excellent. Strong store-level relationships make execution easy.",
          cons: "Company-level communication could be stronger. Sometimes feels siloed between markets.",
        },
        {
          id: "osl-r4",
          rating: 3.0,
          date: "Nov 14, 2025",
          title: "Decent entry point into retail services",
          role: "Sales Associate",
          employmentStatus: "Current employee, <1 year",
          location: "Charlotte, NC",
          recommend: true,
          ceoApproval: null,
          businessOutlook: null,
          pros: "Low barrier to entry, good for learning the Costco and Samsung retail ecosystem.",
          cons: "Inconsistent training across locations. What you learn depends heavily on your manager.",
        },
      ],
    },
  },

  "2020": {
    slug: "2020",
    hq: "Tempe, AZ",
    clientBrands: ["Microsoft", "Samsung", "LG", "Sony", "Bose"],
    operatingIn: ["Best Buy", "Microsoft retail", "Electronics boutiques"],
    totalRolesFound: 267,
    rolesClosed: 189,
    kpis: {
      activePostings: 78,
      newThisWeek: 8,
      avgPayMin: 45000,
      topRole: "Brand Ambassador",
      trend: { direction: "up", pct: "+11%" },
    },
    insight:
      "2020 Companies is running a broad national Brand Ambassador campaign across consumer electronics, with notable expansion into Microsoft retail activations in Texas.",
    narrative:
      "2020 Companies is a full-service outsourced sales and marketing organization operating across consumer electronics, wireless, and home improvement verticals. Their broad brand portfolio — spanning Microsoft, Samsung, LG, Sony, and Bose — reflects a generalist approach to field sales rather than deep specialization in any single brand. The Texas Microsoft expansion is a potential indicator of a new enterprise retail contract.",
    roleDistribution: [
      { role: "Brand Ambassador", count: 38 },
      { role: "Field Sales", count: 22 },
      { role: "Retail Trainer", count: 14 },
      { role: "Area Manager", count: 4 },
    ],
    geographicFocus:
      "Texas, California, New York — high-density metro strategy targeting the three largest consumer electronics markets.",
    payBenchmarks: [
      { role_archetype: "Brand Ambassador", pay_min_avg: 40000, pay_max_avg: 50000 },
      { role_archetype: "Field Sales", pay_min_avg: 44000, pay_max_avg: 56000 },
      { role_archetype: "Retail Trainer", pay_min_avg: 48000, pay_max_avg: 60000 },
      { role_archetype: "Area Manager", pay_min_avg: 64000, pay_max_avg: 80000 },
    ],
    topBrands: [
      { brand_name: "Microsoft", count: 38 },
      { brand_name: "Samsung", count: 26 },
      { brand_name: "LG", count: 18 },
      { brand_name: "Sony", count: 12 },
      { brand_name: "Bose", count: 8 },
    ],
    dataNote:
      "2020 Companies' Workday ATS listings sometimes bundle multiple openings into a single job req. Active posting count may understate true open headcount.",
    postings: [
      {
        id: "2020-1",
        title: "Brand Ambassador – Microsoft",
        location: "Austin, TX",
        role_archetype: "Brand Ambassador",
        is_active: true,
        first_seen_at: "2026-02-14T00:00:00Z",
      },
      {
        id: "2020-2",
        title: "Brand Ambassador – Samsung",
        location: "Los Angeles, CA",
        role_archetype: "Brand Ambassador",
        is_active: true,
        first_seen_at: "2026-02-12T00:00:00Z",
      },
      {
        id: "2020-3",
        title: "Field Sales Representative – LG",
        location: "New York, NY",
        role_archetype: "Field Sales",
        is_active: true,
        first_seen_at: "2026-02-10T00:00:00Z",
      },
      {
        id: "2020-4",
        title: "Retail Trainer – Consumer Electronics",
        location: "Houston, TX",
        role_archetype: "Retail Trainer",
        is_active: true,
        first_seen_at: "2026-02-09T00:00:00Z",
      },
      {
        id: "2020-5",
        title: "Area Manager – West",
        location: "San Francisco, CA",
        role_archetype: "Area Manager",
        is_active: false,
        first_seen_at: "2026-01-22T00:00:00Z",
      },
    ],
    glassdoor: {
      overallRating: 3.8,
      totalReviews: 247,
      recommendPct: 70,
      ceoName: "Dave Haas",
      ceoApprovalPct: 76,
      businessOutlookPct: 65,
      interviewPositivePct: 55,
      interviewDifficulty: 2.8,
      interviewReviewCount: 52,
      ratingsByCategory: [
        { label: "Diversity & inclusion", score: 4.1, trend: "up" },
        { label: "Work/Life balance", score: 3.9, trend: "up" },
        { label: "Culture & values", score: 3.8, trend: "flat" },
        { label: "Compensation & benefits", score: 3.6, trend: "up" },
        { label: "Career opportunities", score: 3.7, trend: "up" },
        { label: "Senior management", score: 3.6, trend: "flat" },
      ],
      reviews: [
        {
          id: "2020-r1",
          rating: 5.0,
          date: "Feb 8, 2026",
          title: "Microsoft program is a standout",
          role: "Brand Ambassador",
          employmentStatus: "Current employee, 1–2 years",
          location: "Austin, TX",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Microsoft Texas expansion is well-resourced. Real investment in specialist training and strong earning potential through demo commissions.",
          cons: "Pace of new program launches sometimes outstrips the onboarding infrastructure.",
        },
        {
          id: "2020-r2",
          rating: 3.0,
          date: "Jan 18, 2026",
          title: "Good brand diversity, inconsistent management",
          role: "Field Sales Representative",
          employmentStatus: "Current employee, 2–3 years",
          location: "New York, NY",
          recommend: true,
          ceoApproval: null,
          businessOutlook: true,
          pros: "Exposure to Microsoft, Samsung, and Bose builds a versatile retail resume.",
          cons: "Regional managers vary wildly in quality. Some markets are well-run, others feel neglected.",
        },
        {
          id: "2020-r3",
          rating: 4.0,
          date: "Dec 10, 2025",
          title: "Best trainer role I've had in retail",
          role: "Retail Trainer",
          employmentStatus: "Current employee, 3–5 years",
          location: "Houston, TX",
          recommend: true,
          ceoApproval: true,
          businessOutlook: true,
          pros: "Real investment in training content. LG and Sony programs have strong curriculum support from the brands themselves.",
          cons: "Travel requirements can be demanding during peak campaign periods.",
        },
        {
          id: "2020-r4",
          rating: 2.0,
          date: "Nov 5, 2025",
          title: "High expectations, limited support",
          role: "Area Manager",
          employmentStatus: "Former employee, 1–2 years",
          location: "San Francisco, CA",
          recommend: false,
          ceoApproval: null,
          businessOutlook: false,
          pros: "Meaningful title and solid experience for your resume.",
          cons: "Area manager span of control is too wide. Managing 12+ stores with one admin budget is untenable.",
        },
      ],
    },
  },
}
