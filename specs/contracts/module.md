---
id: CONTRACTS
title: Contracts module
status: approved
---

# Contracts module

**Service:** `services/contract-service` · **DB schema:** `contracts` · **API base:** `/api/contracts`

Lets a user upload a contract (PDF or Word). The service reads it, extracts the parties, key
dates, terms and risks with AI, stores them in PostgreSQL, and summarises the contracts on a
dashboard. Independent of the Invoices module.

## Features

| ID | Feature | Status |
|---|---|---|
| CON-001 | Upload & AI extraction | requirements approved |
| CON-002 | Contract list & detail | requirements approved |
| CON-003 | Contract dashboard | requirements approved |

## Accepted files

- PDF (`.pdf`) and Word (`.docx`), validated by content (magic bytes) as well as extension.
- Maximum 20 MB. One file per upload.
- The document must contain selectable text. Scanned image-only PDFs are rejected with a clear
  message (OCR is out of scope).

## Processing lifecycle

```
uploaded ──► extracting_text ──► analysing ──► completed
                 │                   │
                 └──────► failed ◄───┘   (error message stored and shown to the user)
```

Extraction runs as a background task. The UI polls `GET /api/contracts/{id}` until
`processing_status` is `completed` or `failed`. A failed contract can be retried.

## Extraction schema

The LLM must return exactly this structure, which is validated with Pydantic (see ADR-0002):

```jsonc
{
  "title": "Master Services Agreement",
  "summary": "Plain-language summary, max ~80 words",
  "parties": [ { "name": "Acme Pvt Ltd", "role": "Client" } ],
  "start_date": "2026-01-01",          // null if not found
  "end_date": "2026-12-31",            // null if not found / open-ended
  "key_dates": [ { "label": "Renewal notice deadline", "date": "2026-11-30", "source_text": "…" } ],
  "terms": [ { "category": "payment|termination|renewal|liability|confidentiality|governing_law|other",
               "summary": "Net 30 days from invoice", "source_text": "…" } ],
  "risks": [ { "severity": "high|medium|low", "title": "Unlimited liability",
               "description": "Why this matters in plain language", "source_text": "…" } ]
}
```

`source_text` is a short quote from the contract, so users can check the AI's work.

## Entities

```
contracts                                 contract_parties / contract_key_dates /
─────────                                 contract_terms / contract_risks
id                 uuid PK                ──────────────────────────────────
file_name          text                   id           uuid PK
file_type          text 'pdf'|'docx'      contract_id  uuid FK → contracts (cascade delete)
stored_path        text                   …fields as in the extraction schema…
file_sha256        text UNIQUE
uploaded_at        timestamptz
processing_status  text (see lifecycle)
error_message      text NULL
title, summary     text
start_date         date NULL
end_date           date NULL
extraction_model   text
raw_extraction     jsonb
created_at / updated_at
```

## Business rules

All rules are computed by the service at read time, relative to **today**. Only contracts with
`processing_status = completed` are counted. The threshold is configurable
(`CONTRACT_AT_RISK_DAYS`, default 3).

### Lifecycle status

Mutually exclusive. Every completed contract has exactly one.

| Status | Rule | Badge |
|---|---|---|
| **In force** | `start_date ≤ today ≤ end_date` (a missing start date counts as started) | Success |
| **Expired** | `end_date < today` | Danger |
| **Not yet started** | `start_date > today` | Neutral |
| **No end date** | `end_date` is null and the contract has started | Info |

### Contract at risk

A flag shown **on top of** the lifecycle status. A contract is **at risk** when **either**
condition holds:

1. It is expiring soon: `today ≤ end_date ≤ today + 3 days`, **OR**
2. It has at least one **high**-severity risk found during extraction.

Expired contracts are not flagged at risk; they already appear as Expired. The UI shows the
reason next to the badge: "Expires in 2 days", "2 high risks", or both.

## API

| Method | Path | Purpose | Feature |
|---|---|---|---|
| POST | `/api/contracts/uploads` | Upload file → `202 {id, processing_status}` | CON-001 |
| POST | `/api/contracts/{id}/retry` | Retry a failed extraction | CON-001 |
| GET | `/api/contracts` | List with `status`, `at_risk`, `q`, sort, paging | CON-002 |
| GET | `/api/contracts/{id}` | Full detail incl. parties, dates, terms, risks | CON-002 |
| GET | `/api/contracts/{id}/file` | Download the original document | CON-002 |
| GET | `/api/contracts/dashboard` | KPI numbers | CON-003 |
| GET | `/health`, `/ready`, `/metrics` | Operations | PLT-002 |

## Decisions

| Question | Decision |
|---|---|
| At risk | Expiring within 3 days **OR** has a high-severity risk (expired contracts excluded) |
| "Not yet started" on the dashboard | Gets its own KPI card |
| Word format | `.docx` only (no legacy `.doc`) |
| Deleting contracts | Not allowed in the POC |
| Same file uploaded twice | Detected by SHA-256 hash of the file; not stored again. The user sees "This contract was already uploaded on <date>" with a link to it. |

## Open questions

- None.
