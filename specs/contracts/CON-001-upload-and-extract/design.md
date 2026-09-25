---
id: CON-001
title: Contract upload and AI extraction — design
status: approved
requirements: ./requirements.md
---

# CON-001 — Design

## Overview

```
UploadContractPage ──multipart──► POST /api/contracts/uploads
                                    1. size ≤ 20 MB, type by content (PDF / DOCX)      ─► 400/413
                                    2. SHA-256 → already uploaded?                     ─► 409 DUPLICATE_CONTRACT
                                    3. store file, insert contract (status=uploaded)
                  ◄── 202 {id, processing_status} ──┘   (well under 2 s — AC2)
      navigate to /contracts/{id}  (CON-002 detail page shows progress, then the result — AC8)

background task (same process, max 2 at a time):
   extracting_text ──► pdfplumber / python-docx → plain text (+ page count)
        │  < 200 visible characters → failed "looks like a scanned image" (AC6)
        ▼
   analysing ──► Claude (structured JSON output) ──► Pydantic validation ──► quote check
        │  API error / invalid output → retry once (AC7) → failed "We couldn't read this contract…"
        ▼
   completed: title, summary, dates, parties, key dates, terms, risks saved in ONE transaction (AC5)
```

The browser polls `GET /api/contracts/{id}` every 2 seconds while the status is not final.

## API

### `POST /api/contracts/uploads`

`multipart/form-data`, field `file`.

| Outcome | HTTP | Body |
|---|---|---|
| Accepted | **202** | `{"id": "…", "processing_status": "uploaded"}` |
| Over 20 MB | 413 | `FILE_TOO_LARGE`: "This file is larger than 20 MB. Please upload a smaller file." |
| Not PDF/DOCX by content (incl. legacy `.doc`, renamed files) | 400 | `INVALID_FILE_TYPE`: "Please upload a PDF or Word (.docx) file." |
| Password-protected DOCX | 400 | `FILE_PROTECTED`: "This file is password-protected. Please remove the password and try again." |
| Same file already uploaded (AC3a) | **409** | `DUPLICATE_CONTRACT`: "This contract was already uploaded on 24 Sep 2026." `details: {contract_id, uploaded_at}` |

**Type detection:** PDF = starts with `%PDF-`. DOCX = ZIP containing `word/document.xml`. An OLE
file (`D0 CF 11 E0…`) is either a legacy `.doc` (→ `INVALID_FILE_TYPE`, with the message "Please
save it as .docx…") or an encrypted `.docx` (contains `EncryptionInfo` → `FILE_PROTECTED`). The
checks mirror INV-001.

### `POST /api/contracts/{id}/retry` (AC9)

Only allowed when `processing_status = failed`, otherwise 409 `NOT_RETRYABLE`. It clears the
error and any partial data, sets `uploaded`, schedules extraction again, and returns
`202 {id, processing_status}`.

`GET /api/contracts/{id}` and `GET /api/contracts/{id}/file` are specified in CON-002.

## Data (migration `0001_create_contract_tables`, schema `contracts`)

```
contracts
  id uuid PK · file_name text · file_type text ('pdf'|'docx') · file_size int
  file_sha256 text UNIQUE · stored_path text · uploaded_at timestamptz
  processing_status text  CHECK IN ('uploaded','extracting_text','analysing','completed','failed')
  error_code text NULL · error_message text NULL          -- message is user-facing
  processing_started_at / processing_finished_at timestamptz NULL
  page_count int NULL · text_chars int NULL
  title text NULL · summary text NULL · start_date date NULL · end_date date NULL
  extraction_model text NULL · raw_extraction jsonb NULL
  input_tokens / output_tokens / cache_read_tokens int NULL
  created_at / updated_at

contract_parties    (id, contract_id FK cascade, position int, name text, role text)
contract_key_dates  (id, contract_id, position, label text, date date, source_text text, source_verified bool)
contract_terms      (id, contract_id, position, category text CHECK IN (payment, termination,
                     renewal, liability, confidentiality, governing_law, other),
                     summary text, source_text text, source_verified bool)
contract_risks      (id, contract_id, position, severity text CHECK IN ('high','medium','low'),
                     title text, description text, source_text text, source_verified bool)
indexes: contracts(end_date), contracts(processing_status), contract_risks(contract_id, severity)
```

Deleting is out of scope, but cascades keep a retry clean: the retry deletes a contract's child
rows before re-extracting.

## Text extraction

| Type | Library | What is kept |
|---|---|---|
| PDF | `pdfplumber` | Page text in order, separated by `\n\n[Page N]\n\n` markers so quotes and page references stay meaningful. An encrypted PDF fails with "This PDF is password-protected…". |
| DOCX | `python-docx` | Paragraphs in body order, plus table cells (row by row, cells joined with ` · `). Headers and footers are ignored. |

- **Scanned document (AC6):** fewer than 200 non-whitespace characters in total → `failed`,
  `error_code = NO_TEXT`, with the exact message from AC6.
- **Too long:** more than 500,000 characters (roughly 300+ pages) → `failed`, `TOO_LONG`, "This
  contract is too long to read automatically (over about 300 pages)." The text is **never
  silently truncated**.
- Extraction runs in a worker thread (`asyncio.to_thread`) so the API stays responsive.

## AI extraction (ADR-0002, revised)

**Client:** `anthropic.AsyncAnthropic` (Python SDK 1.x), created once at startup from
`ANTHROPIC_API_KEY`. Its built-in retries (2, with backoff, for connection errors, 429 and 5xx)
handle transient faults.

**Request** (`app/extraction/claude.py`):

| Setting | Value | Why |
|---|---|---|
| `model` | `CONTRACT_LLM_MODEL`, default **`claude-sonnet-5`** | Product-owner decision (cost), per ADR-0002. `claude-opus-5` can be set for more careful risk judgement. |
| Thinking | `{type: "adaptive"}` | Better risk assessment |
| `output_config.effort` | `CONTRACT_LLM_EFFORT`, default `high` | Extraction with judgement. Can be lowered to `medium` for cost. |
| `output_config.format` | `json_schema` = the extraction schema | **Guarantees** a schema-valid JSON response |
| Streaming | `messages.stream(…)` + `get_final_message()`, `max_tokens = 32000` | Long outputs never hit HTTP timeouts |
| Caching | top-level automatic `cache_control` | The system prompt and schema are the same for every contract; a retry of the same contract re-reads its text from the cache |
| `system` | fixed instructions (below) | Stable prefix, so it caches well |
| `messages` | one user turn: `<contract file_name="…">…text…</contract>` + "Extract the contract details." | |

**System prompt (outline):** "You read business contracts for a small Indian business owner…"
It asks for:
- Plain English, and a summary of 80 words at most.
- Every party with its role as the contract names it (e.g. Client, Supplier).
- Start and end dates exactly as stated (`null` if absent or open-ended), in ISO form, reading
  dates day-first.
- Key dates: renewal and notice deadlines, payment milestones.
- Terms in the fixed categories.
- **Risks from the small business's point of view**, rated high/medium/low with a one-line
  "why it matters", covering things like unlimited liability, one-sided termination, auto-renewal
  traps, short notice, missing SLAs and one-sided arbitrator appointment.
- `source_text` must be a short (≤ 300 characters) **verbatim** quote from the contract.

The contract text is untrusted: the prompt tells the model to treat everything inside `<contract>`
as data, never as instructions. No tools are offered, so a malicious document can at most distort
its own extraction.

**Schema** (`app/extraction/schema.py`): Pydantic models are the single source. The JSON schema
sent to the API is generated from them (`additionalProperties: false`, every field required,
nullable fields as `["string","null"]`, enums for category and severity). Dates are
`YYYY-MM-DD` strings, parsed by Pydantic afterwards. Limits: at most 20 parties, 40 key dates,
60 terms and 40 risks.

**Response handling:**

| Result | Action |
|---|---|
| `stop_reason = end_turn`, JSON parses, Pydantic validates | ✔ continue to the quote check |
| `stop_reason = max_tokens` or `refusal`, invalid JSON or dates, SDK error after its own retries, or timeout | **retry once** (AC7); if it fails again → `failed`, `error_code = AI_FAILED`, "We couldn't read this contract automatically. Please try again, or check the file." |
| Missing API key | `failed`, `error_code = AI_NOT_CONFIGURED`, "Contract reading isn't set up yet. Please ask your administrator to add the AI key." (`/ready` already reports this, per PLT-002) |

**Quote check (supports AC6/AC10):** each `source_text` is matched against the extracted text,
ignoring case, whitespace and quote-mark style. It is stored with `source_verified = true/false`.
Unverified quotes are kept, but the UI marks them (CON-002). Nothing the AI returns is trusted
blindly.

**Stale jobs:** at startup, any contract left in `extracting_text` / `analysing` for more than 15
minutes (for example after a restart) is set to `failed` with "Reading was interrupted. Please
try again."

## Code structure (contract-service)

```
app/api/uploads.py            POST /uploads, POST /{id}/retry
app/domain/file_types.py      size + content sniffing (like INV-001)
app/domain/text_extraction.py PDF/DOCX → text, NO_TEXT / TOO_LONG checks
app/extraction/schema.py      Pydantic extraction models → JSON schema
app/extraction/prompt.py      system prompt + user message builder
app/extraction/claude.py      ClaudeExtractor (AsyncAnthropic, stream, parse, usage)
app/extraction/quotes.py      normalised quote matching
app/domain/pipeline.py        background job: statuses, retry-once, persistence, logs/metrics
app/db/models.py, contract_repo.py
```

`pipeline.py` depends on an `Extractor` protocol, so every test uses a fake extractor and **no
automated test calls the real API**. One opt-in live test (`pytest -m llm`, which needs
`ANTHROPIC_API_KEY` and `RUN_LLM_TESTS=1`) runs the two sample contracts end to end.

## UI — `/contracts/upload`

This mirrors the invoice upload page, reusing `FileDropzone` with `accept=['.pdf','.docx']`,
20 MB and the help text "PDF or Word (.docx), up to 20 MB" (AC1). It adds a short "What happens
next" list: "We read the contract · pick out parties, dates, terms and risks · usually takes under
a minute".
- **On 202:** the page navigates to `/contracts/{id}`, which shows the progress (CON-002).
- **On 409:** an info alert, "This contract was already uploaded on 24 Sep 2026.", with an
  **Open the existing contract** button.
- **Other errors:** `ErrorAlert` titled "We couldn't use this file", and the file stays selected.

## Observability (PLT-002)

| Event | Fields (never document text or extracted content) |
|---|---|
| `contract_upload.received` / `.rejected` | `file_type`, `size_bytes`, `code` |
| `contract_extraction.started` | `contract_id`, `attempt` |
| `contract_extraction.completed` | `contract_id`, `duration_ms`, `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `pages`, counts of parties/dates/terms/risks, `unverified_quotes` |
| `contract_extraction.failed` | `contract_id`, `error_code`, `attempt`, technical `reason` (exception class / stop_reason) |

Metrics: `contract_uploads_total{result}`, `contract_extractions_total{result}`,
`contract_extraction_duration_seconds{model}`, and `llm_tokens_total{model,direction}` with
`direction` ∈ `input | output | cache_read | cache_write`. These are already on the Grafana
dashboard.

## Edge cases

| Case | Behaviour |
|---|---|
| The same file is uploaded twice at the same moment | The unique `file_sha256` makes the second insert fail → 409 |
| A contract with no dates at all | Stored with nulls → lifecycle "No end date" (module.md) |
| The AI returns an end date before the start date | Kept as extracted; the detail page shows a "Please check these dates" note |
| Very long risk list | Capped by the schema limits; the prompt asks for the most important items first |
| The service restarts mid-extraction | Stale-job sweep → failed → Try again |

## Testing

| AC | Tests |
|---|---|
| AC1 | Vitest: dropzone accepts .pdf/.docx, rejects others and oversize files |
| AC2 | API: 202 in < 2 s; file stored; row `uploaded` |
| AC3 | API: renamed PDF/text, legacy .doc, encrypted docx, 20 MB + 1 byte → codes; nothing stored |
| AC3a | API: second identical upload → 409 with the first contract's id/date; still one row |
| AC4, AC5 | Pipeline with a fake extractor → all tables filled, `completed`, model + usage stored. Unit: the request builder sends the schema, model, effort, stream and fallbacks. |
| AC6 | Pipeline: image-only PDF fixture (a PDF with no text layer) → `failed` + exact message, extractor never called |
| AC7 | Fake extractor fails once then succeeds → completed; fails twice → failed with the friendly message; `contract_extraction.failed` logged |
| AC8, AC9 | Playwright (fake extractor via `CONTRACT_EXTRACTOR=fake` in e2e): upload → detail shows progress → result; forced failure → Try again → completed |
| AC10 | Schema rejects missing severity / source_text; quote check marks unverified quotes |
| AC11 | Log capture: events and fields present; no document text in any line |
| Live | `pytest -m llm`: both sample contracts. The MSA comes back with ≥ 1 high risk and an end date 2 days after generation; the supply agreement comes back in force. |

`CONTRACT_EXTRACTOR=fake` is a test-only setting that selects a deterministic extractor producing
plausible data from the document text. It lets e2e tests run without an API key or cost.
