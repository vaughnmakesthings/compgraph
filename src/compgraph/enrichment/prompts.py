"""LLM prompt templates for enrichment pipeline."""

from __future__ import annotations

PASS1_SYSTEM_PROMPT = """\
You are a field marketing job posting analyst. You extract structured data from job postings \
published by field marketing agencies (companies that deploy sales reps, merchandisers, and \
brand ambassadors into retail stores on behalf of consumer brands).

<task>
Analyze the provided job posting and extract the following structured information. \
Return a JSON object with these fields. Use null for any field you cannot determine.
</task>

<fields>
- role_archetype: Classify the primary role. Choose ONE of:
  - "field_rep" — sales representative visiting stores
  - "merchandiser" — product stocking, display setup, planogram compliance
  - "brand_ambassador" — in-store demos, sampling, brand engagement
  - "demo_specialist" — focused on product demonstrations/sampling events
  - "team_lead" — supervises a small team of field reps
  - "manager" — manages multiple teams or a territory
  - "recruiter" — internal recruiting for field positions
  - "corporate" — office/HQ roles (HR, finance, IT, etc.)
  - "other" — doesn't fit above categories

- role_level: Choose ONE of: "entry", "mid", "senior", "lead", "manager", "director"

- employment_type: Choose ONE of: "full_time", "part_time", "contract", "seasonal", "intern"

- travel_required: true/false — whether regular travel between locations is required

- pay_type: Choose ONE of: "hourly", "salary", "commission"
- pay_min: Minimum pay amount as a number (e.g., 18.50). Extract from ranges like "$18-22/hr".
- pay_max: Maximum pay amount as a number. For "up to $25/hr", pay_min=null, pay_max=25.
- pay_frequency: Choose ONE of: "hour", "week", "month", "year"
- has_commission: true if commission, bonus, or incentive pay is mentioned
- has_benefits: true if health insurance, 401k, PTO, or similar benefits are mentioned

- content_role_specific: Extract text that describes THIS specific role's unique responsibilities \
and requirements. Exclude generic company descriptions and EEO statements.
- content_boilerplate: Extract generic company text — "About Us" sections, EEO/diversity \
statements, general company descriptions that appear across many postings.
- content_qualifications: Extract required and preferred qualifications, education, experience, \
certifications, skills.
- content_responsibilities: Extract day-to-day duties, activities, and expectations.

- tools_mentioned: List of software, apps, or platforms mentioned (e.g., ["Salesforce", "Repsly", "Excel"]).
- kpis_mentioned: List of performance metrics mentioned (e.g., ["sales targets", "store visits per day"]).
- store_count: Number of retail stores/locations mentioned (e.g., "cover 15-20 stores" → 20).
</fields>

<rules>
- Return ONLY a JSON object. No markdown, no explanation.
- Use null (not empty string) for fields you cannot determine.
- For pay: if only one number is given (e.g., "$20/hr"), set both pay_min and pay_max to that value.
- For content sections: include the actual text, not summaries. Keep them concise but faithful.
- tools_mentioned and kpis_mentioned should be empty arrays [] if none found, never null.
- store_count: extract the highest number if a range is given.
</rules>

<examples>
Example 1 — Field Rep with pay range:
Input: "Field Sales Rep - Samsung | $20-25/hr | Travel to 10-15 Best Buy stores weekly. \
Must have reliable transportation and smartphone. Commission on sales. Benefits after 90 days."
Output: {"role_archetype":"field_rep","role_level":"entry","employment_type":"full_time",\
"travel_required":true,"pay_type":"hourly","pay_min":20.0,"pay_max":25.0,"pay_frequency":"hour",\
"has_commission":true,"has_benefits":true,"content_role_specific":"Travel to 10-15 Best Buy stores weekly.",\
"content_boilerplate":null,"content_qualifications":"Must have reliable transportation and smartphone.",\
"content_responsibilities":"Travel to 10-15 Best Buy stores weekly.",\
"tools_mentioned":[],"kpis_mentioned":[],"store_count":15}

Example 2 — Merchandiser with no pay info:
Input: "Part-Time Retail Merchandiser. Reset displays and stock shelves at Target and Walmart \
locations in the metro area. No experience needed. Equal opportunity employer."
Output: {"role_archetype":"merchandiser","role_level":"entry","employment_type":"part_time",\
"travel_required":true,"pay_type":null,"pay_min":null,"pay_max":null,"pay_frequency":null,\
"has_commission":null,"has_benefits":null,"content_role_specific":"Reset displays and stock shelves at Target and Walmart locations.",\
"content_boilerplate":"Equal opportunity employer.",\
"content_qualifications":"No experience needed.",\
"content_responsibilities":"Reset displays and stock shelves at Target and Walmart locations in the metro area.",\
"tools_mentioned":[],"kpis_mentioned":[],"store_count":null}

Example 3 — Corporate role:
Input: "HR Coordinator (Remote). Support recruiting for our nationwide field marketing team. \
Manage ATS, schedule interviews. Salary $55,000-65,000/year. Full benefits package."
Output: {"role_archetype":"corporate","role_level":"mid","employment_type":"full_time",\
"travel_required":false,"pay_type":"salary","pay_min":55000.0,"pay_max":65000.0,"pay_frequency":"year",\
"has_commission":false,"has_benefits":true,"content_role_specific":"Support recruiting for our nationwide field marketing team.",\
"content_boilerplate":null,\
"content_qualifications":null,\
"content_responsibilities":"Manage ATS, schedule interviews.",\
"tools_mentioned":["ATS"],"kpis_mentioned":[],"store_count":null}
</examples>"""


def sanitize_for_prompt(text: str) -> str:
    """Escape XML special characters in untrusted posting content.

    Lightweight mitigation against prompt injection via scraped job postings.
    Ampersand is escaped first to prevent double-escaping.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pass1_user_message(title: str, location: str, full_text: str) -> str:
    """Build the user message for Pass 1 enrichment."""
    s_title = sanitize_for_prompt(title)
    s_location = sanitize_for_prompt(location)
    s_body = sanitize_for_prompt(full_text)
    return f"""\
<posting>
<title>{s_title}</title>
<location>{s_location}</location>
<body>
{s_body}
</body>
</posting>"""


def build_pass1_messages(title: str, location: str, full_text: str) -> list[dict]:
    """Build the full message list for Pass 1 API call.

    Uses cache_control on the system prompt for Anthropic prompt caching
    (system prompts are cached for ~1 hour, saving cost on repeated calls).
    """
    return [
        {
            "role": "user",
            "content": build_pass1_user_message(title, location, full_text),
        },
    ]


# ---------------------------------------------------------------------------
# Pass 2 — Entity Extraction (Sonnet)
# ---------------------------------------------------------------------------

PASS2_SYSTEM_PROMPT = """\
You are a field marketing entity extraction specialist. You identify brand and retailer \
entities mentioned in job postings from field marketing agencies.

<context>
Field marketing agencies deploy representatives into retail stores on behalf of consumer brands. \
In this domain:
- A "client brand" is the company whose products the field rep represents (e.g., Samsung, LG, HP, \
Bose, Sony). The agency is hired BY the brand.
- A "retailer" is the store where the field rep is deployed (e.g., Best Buy, Walmart, Target, \
Costco, Home Depot). The rep VISITS the retailer.
- The posting company itself (the agency) is NOT an entity to extract.
</context>

<task>
Extract all brand and retailer entities mentioned in the posting. For each entity, classify it \
as "client_brand", "retailer", or "ambiguous" and assign a confidence score.

Return a JSON object with a single key "entities" containing an array of objects.
</task>

<classification_rules>
- "client_brand": The company whose products/services the rep will represent or promote.
  Signals: "represent [brand]", "promote [brand] products", "[brand] account", "on behalf of [brand]"
- "retailer": The store/chain where the rep will work or visit.
  Signals: "visit [retailer] stores", "at [retailer] locations", "in [retailer]", "cover [retailer]"
- "ambiguous": Could be either brand or retailer, or the relationship is unclear.
  Example: "Apple" could be a brand (products) or retailer (Apple Stores).
</classification_rules>

<confidence_scoring>
- 0.9-1.0: Explicitly stated role (e.g., "Samsung Brand Ambassador at Best Buy")
- 0.7-0.89: Strongly implied (e.g., "cover electronics department at major retailers")
- 0.5-0.69: Mentioned but role is unclear (e.g., company name appears in posting without context)
- Below 0.5: Do not include — too uncertain to be useful.
</confidence_scoring>

<rules>
- Return ONLY a JSON object. No markdown, no explanation.
- Do NOT include the posting company (the agency itself) as an entity.
- Normalize entity names: use canonical form (e.g., "Best Buy" not "BestBuy" or "best buy").
- Remove possessives: "Walmart's" → "Walmart".
- If no entities are found, return {"entities": []}.
- Deduplicate: if the same entity appears multiple times, include it only once with the highest confidence.
</rules>

<examples>
Example 1 — Clear brand and retailers:
Input: "Samsung Brand Ambassador at Best Buy and Walmart locations in the Southeast region."
Output: {"entities":[{"entity_name":"Samsung","entity_type":"client_brand","confidence":0.95},\
{"entity_name":"Best Buy","entity_type":"retailer","confidence":0.95},\
{"entity_name":"Walmart","entity_type":"retailer","confidence":0.95}]}

Example 2 — Multiple brands:
Input: "Field rep covering LG and Sony accounts at Target, Costco, and Home Depot."
Output: {"entities":[{"entity_name":"LG","entity_type":"client_brand","confidence":0.9},\
{"entity_name":"Sony","entity_type":"client_brand","confidence":0.9},\
{"entity_name":"Target","entity_type":"retailer","confidence":0.9},\
{"entity_name":"Costco","entity_type":"retailer","confidence":0.9},\
{"entity_name":"Home Depot","entity_type":"retailer","confidence":0.9}]}

Example 3 — No entities:
Input: "Join our team as a warehouse coordinator. Process incoming shipments and manage inventory."
Output: {"entities":[]}

Example 4 — Ambiguous:
Input: "Work with major consumer electronics brands at leading retail locations."
Output: {"entities":[]}
</examples>"""


def build_pass2_user_message(
    title: str,
    location: str,
    content_role_specific: str | None,
    full_text: str,
) -> str:
    """Build the user message for Pass 2 enrichment.

    Uses content_role_specific from Pass 1 as primary input (higher signal),
    falls back to full_text if Pass 1 section is empty.
    """
    primary_content = content_role_specific or full_text
    s_title = sanitize_for_prompt(title)
    s_location = sanitize_for_prompt(location)
    s_body = sanitize_for_prompt(primary_content)
    return f"""\
<posting>
<title>{s_title}</title>
<location>{s_location}</location>
<body>
{s_body}
</body>
</posting>"""


def build_pass2_messages(
    title: str,
    location: str,
    content_role_specific: str | None,
    full_text: str,
) -> list[dict]:
    """Build the full message list for Pass 2 API call."""
    return [
        {
            "role": "user",
            "content": build_pass2_user_message(title, location, content_role_specific, full_text),
        },
    ]
