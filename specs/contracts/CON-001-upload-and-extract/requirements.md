---
id: CON-001
title: Contract upload and AI extraction
status: draft
depends_on: [CONTRACTS, PLT-001, PLT-002, ADR-0002]
---

# CON-001 — Contract upload and AI extraction

## Goal

A user uploads a PDF or Word contract, and the system extracts and stores its parties, key dates,
terms and risks, without the user needing to read the whole document.

## User stories

- As a business owner, I want to upload a contract file, so that I don't have to read and summarise it myself.
- As a business owner, I want to know what's happening while the contract is being read, so that I don't think the app is stuck.
- As a business owner, I want a clear message if the file can't be read, so that I know what to do instead.

## Acceptance criteria

| ID | Criterion |
|---|---|
| CON-001-AC1 | THE SYSTEM SHALL provide an Upload contract page with a drop zone and a "Choose file" button, stating "PDF or Word (.docx), up to 20 MB". |
| CON-001-AC2 | WHEN a valid PDF or DOCX file is uploaded THE SYSTEM SHALL store the original file, create a contract with `processing_status = uploaded`, and respond within 2 seconds with the contract ID. |
| CON-001-AC3 | IF the file is not a real PDF/DOCX (checked by content, not just extension) or is over 20 MB THEN THE SYSTEM SHALL reject it without storing it, with a plain-language message naming the accepted formats and size. |
| CON-001-AC4 | WHEN a contract is uploaded THE SYSTEM SHALL extract its text and send it to the configured Claude model, requesting the extraction schema in `contracts/module.md`. |
| CON-001-AC5 | WHEN the AI response is valid against the schema THE SYSTEM SHALL save the title, summary, parties, start/end dates, key dates, terms and risks, plus the raw extraction and model name, and set `processing_status = completed`. |
| CON-001-AC6 | IF the document contains no extractable text (e.g. a scanned PDF) THEN THE SYSTEM SHALL set `processing_status = failed` with the message "This file looks like a scanned image. Please upload a text-based PDF or Word document." |
| CON-001-AC7 | IF the AI call fails or returns invalid data THEN THE SYSTEM SHALL retry once automatically; if it still fails, set `processing_status = failed` with a user-friendly message and log the technical reason. |
| CON-001-AC8 | WHILE a contract is processing THE SYSTEM SHALL show a progress message on screen, and WHEN processing finishes THE SYSTEM SHALL take the user to the contract's detail page (CON-002). |
| CON-001-AC9 | WHEN a contract has failed THE SYSTEM SHALL offer a "Try again" button that re-runs extraction on the stored file. |
| CON-001-AC10 | THE SYSTEM SHALL assign every risk a severity of high, medium or low, and give every term, risk and key date a short `source_text` quote from the document. |
| CON-001-AC11 | THE SYSTEM SHALL log the upload, extraction duration, model and token usage, without logging the document content (PLT-002). |

## Out of scope

- OCR for scanned documents; `.doc` (legacy Word) files; uploading several files at once.
- Editing or correcting the extracted data.

## Open questions

- How should duplicate uploads of the same file be handled? (module.md Q1; proposal: detect by
  file hash and link to the existing contract.) _Resolved: `.docx` only._
