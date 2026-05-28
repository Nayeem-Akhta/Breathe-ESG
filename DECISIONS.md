# Decisions

## Ambiguities Resolved

### 1. SAP Export Format
**Ambiguity:** SAP supports IDoc, flat file, OData, and BAPI exports.
Which should we handle?

**Decision:** Flat file CSV export.

**Reasoning:** In practice, enterprise clients are most likely to
send a CSV export from SAP's standard reporting tools (SE16, MB51).
IDoc is an EDI format requiring specialized parsing libraries and
middleware. OData requires authenticated API access to the client's
SAP system — impractical for a data ingestion prototype. Flat file
CSV is realistic, testable, and represents what a client's IT team
would actually export and email to a data team.

**What I'd ask the PM:** "Does the client have an IT team who can
expose an OData endpoint, or are they emailing CSV exports? What's
the typical file size — are we talking 500 rows or 5 million?"

### 2. Utility Data Format
**Ambiguity:** Facilities teams get electricity data as PDFs, portal
CSVs, or APIs.

**Decision:** Portal CSV export.

**Reasoning:** PDF parsing is fragile — bill layouts change between
utilities and between years. Utility APIs exist for some providers
(e.g., BESCOM's API in Karnataka) but are not standardized and
require per-utility integration work. Portal CSV exports are the
realistic middle ground — structured, consistent within a utility,
and what a facilities manager would actually produce when asked
"export your electricity data."

**What I'd ask the PM:** "How many utility providers does this client
have? Are they all in India or across multiple countries? Do they
want us to handle PDF bills or only structured exports?"

### 3. Travel Data Format
**Ambiguity:** Concur, Navan, and similar platforms have different
API structures and export formats.

**Decision:** CSV export modeled on Concur's standard trip report.

**Reasoning:** Concur's API requires OAuth2 authentication and
per-company configuration. For a prototype, a CSV export from
Concur's standard "Trip Report" export captures the same fields.
The CSV structure (trip_id, employee_id, travel_date, travel_type,
origin, destination, distance_km, travel_class) reflects what
Concur actually exports based on their public documentation.

**What I'd ask the PM:** "Does the client use Concur or Navan?
Do they have an IT team who can set up API access, or should we
plan for CSV exports? Do they need hotel nights or only flights?"

### 4. Distance Calculation for Flights
**Ambiguity:** Travel data often provides only airport codes (BLR, LHR)
without distances.

**Decision:** Static lookup table of common routes, with flagging for
unknown pairs.

**Reasoning:** In production, we would use the ICAO or OAG aviation
API to calculate great-circle distances between any airport pair.
For this prototype, a static lookup of realistic routes covers the
sample data while demonstrating the pattern. Unknown airport pairs
are flagged as suspicious rather than silently dropped — the analyst
sees them and can investigate.

**What I'd ask the PM:** "Do we have a budget for an aviation distance
API? ICAO and OAG both have paid APIs. Alternatively, we could use
the open-source `airportsdata` Python package for coordinates and
calculate haversine distances ourselves."

### 5. Multi-tenancy Enforcement
**Ambiguity:** How strictly should tenant isolation be enforced?

**Decision:** organization_id required on every API call, filtered
at the query level.

**Reasoning:** Every API endpoint requires an `organization_id`
parameter and filters all queries by it. This prevents cross-tenant
data leakage even if authentication is weak. In production, this
would be replaced by JWT authentication where the org is extracted
from the token — removing the need to pass it as a parameter.

### 6. Emission Factors
**Ambiguity:** Which emission factor database to use?

**Decision:** DEFRA 2023 for fuel and travel, CEA India 2023 for
electricity.

**Reasoning:** DEFRA (UK Department for Environment) publishes annual
greenhouse gas conversion factors that are widely used in corporate
carbon reporting globally. For Indian electricity, the Central
Electricity Authority (CEA) publishes grid emission factors by
region, which are more accurate than using a global average.

### 7. What Counts as Suspicious
**Ambiguity:** What thresholds should trigger automatic flagging?

**Decision:** Two rules implemented:
- Unknown plant code (not in PlantLookup table)
- Quantity > 50,000 litres in a single SAP entry

**Reasoning:** These cover the two most common real-world data quality
issues: plant codes from test systems or decommissioned plants, and
accidental entry of cumulative rather than periodic quantities.

**What I'd ask the PM:** "Do you have historical data we could use
to set statistical thresholds (e.g., flag values > 3 standard
deviations from 3-month average)? That would be more defensible
than hardcoded limits."

---

## What I Would Ask the PM

1. What is the expected file size per upload? (500 rows vs 500,000 rows
   changes the architecture significantly — async processing needed above ~10k rows)
2. Does the client need to handle multiple currencies in travel spend?
3. Should rejected entries be re-submittable or permanently excluded?
4. What is the audit report format — does it need to conform to GHG
   Protocol, CDP, or a custom template?
5. Is real-time ingestion (API polling) a near-term requirement, or
   is batch file upload sufficient for the next 12 months?