# Tradeoffs

## Three Things Deliberately Not Built

### 1. Authentication and Authorization
**What it would look like:** JWT-based authentication, per-user
permissions, organization-scoped API tokens, login/logout flow in
the React frontend.

**Why not built:** The assignment asked for a prototype demonstrating
data ingestion, normalization, and analyst review. Implementing auth
would have consumed roughly 30% of the available time for something
that doesn't demonstrate the core competency being evaluated.
The multi-tenancy model is fully designed and the API enforces
organization filtering — dropping in JWT auth is a well-understood
engineering task that would not require model changes.

**What breaks without it:** In production, any user can call any
API endpoint. This is acceptable for a prototype with sample data
but not for real client data.

### 2. Asynchronous Ingestion Processing
**What it would look like:** File uploads would queue a Celery task,
return immediately with a batch_id, and the client would poll for
status. This is necessary for files with more than ~10,000 rows.

**Why not built:** The sample data has 8-20 rows per file. Synchronous
processing works fine at this scale. Adding Celery requires Redis as
a message broker, a separate worker process, and significantly more
deployment complexity — all for a problem that doesn't exist at
prototype scale.

**What breaks without it:** Uploading a real SAP export with 50,000
rows would cause the HTTP request to time out (typically at 30
seconds on Render's free tier). The fix is well understood but
out of scope for this prototype.

### 3. PDF Bill Parsing for Utility Data
**What it would look like:** Using a library like `pdfplumber` or
`camelot` to extract tables from utility bill PDFs, with
per-utility parsing rules to handle different bill layouts.

**Why not built:** PDF parsing is brittle — bill layouts change
between utilities, between years, and sometimes between billing
cycles. Building reliable PDF parsing for even three utility
providers would require significant reverse-engineering of each
provider's format and ongoing maintenance when layouts change.
The CSV export approach is more reliable and covers the same data.
The tradeoff is that a facilities manager needs to export a CSV
rather than simply forwarding a PDF email — a reasonable ask.

**What I'd build next given more time:** A hybrid approach where
the system accepts both CSV and PDF, uses heuristic parsing on PDFs,
and flags low-confidence extractions for manual review.