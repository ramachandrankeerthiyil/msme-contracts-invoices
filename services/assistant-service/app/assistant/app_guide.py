"""A guide to the app, for answering "what is this app?" and "how does it work?" (AST-002 AC7).

Facts for the model to explain in its own words. It is sent in the cached system prompt, so keep
it stable. The at-risk windows are filled in from settings (AC8). When the app changes, change
this guide: `tests/assistant/test_guardrails.py` holds it to the outline in the AST-002 design.
"""

APP_SUMMARY = (
    "This app helps small businesses keep track of their contracts and invoices, and shows what "
    "needs attention this week. You upload your contracts (PDF or Word) and an invoice "
    "spreadsheet (Excel), and the app flags what is overdue, what is due soon and which "
    "contracts are about to end or carry risks. You can also ask me questions about your own "
    "contracts and invoices."
)

_GUIDE = """\
# Guide to this app

## What the app is
{summary} There is no account or login in this version: anyone who can open the app sees the \
same data.

## Contracts
- **Upload:** on the Upload contract page, add a PDF or Word contract. The app reads it with AI \
(usually under a minute) and shows the parties, the key dates, the main terms and the risks, \
each with a quote from the document so it can be checked.
- **Pages:** Contracts Dashboard (the numbers that need attention), All contracts (a searchable \
list) and Upload contract.
- **Statuses:** In force (started and not ended), Not yet started, Expired, and No end date. A \
contract is **at risk** if it ends within {contract_days} days or has a high-severity risk. \
Scanned (image-only) documents cannot be read.

## Invoices
- **Upload:** on the Upload invoices page, add an Excel (.xlsx) sheet with these columns: \
Invoice Number, Customer Name, Date Raised, Due Date, Amount and Paid Date (leave Paid Date \
blank if unpaid). A template can be downloaded there. Customer Email is optional but is needed \
for email reminders.
- **Updating:** uploading a sheet that contains an invoice number the app already has updates \
that invoice. This is how to record a payment (fill in the Paid Date and upload again) or to \
correct an amount. Invoices cannot be edited by typing in the app.
- **Statuses** (worked out from today's date every time you look): **Paid** (has a Paid Date); \
**Outstanding** (unpaid and past its due date); **At risk** (unpaid and due within \
{invoice_days} days); **Open** (unpaid and due later). **Needs follow-up** means Outstanding \
plus At risk.
- **Pages:** Invoices Dashboard (this week: the 7 days starting from the latest upload, by due \
date; value, follow-ups and top invoices to chase), All invoices (tabs for each status, search, \
sorting and an Excel export) and Upload invoices.

## Email reminders
On the All invoices page, every Outstanding invoice has a **Send email reminder** button. It \
opens a drafted, polite email to the customer's address from the sheet's Customer Email column. \
You can read and edit it, then send it. Nothing is sent until you click Send. If the sheet has no \
email address for that customer, the app says so and asks you to add it and upload again. \
Reminders are only for Outstanding invoices.

## Talk to Me (this assistant)
It answers questions about your own contracts and invoices from your live data, shows what it \
looked up, links to each record, and explains this app. It can only look things up: it cannot \
change anything, send anything or give legal advice, and it can make mistakes, so important \
details should be checked on the contract or invoice page. It only talks about the app, \
contracts and invoices.

## How it works
- The app has a web page you use, and separate services behind it for contracts, invoices and \
this assistant. The contracts and invoices are kept in a database.
- Uploaded contract text is sent to Anthropic's Claude AI service so it can be read, and your \
questions to Talk to Me are sent to Claude to write answers. Talk to Me never changes any data.
- Amounts are in Indian rupees (INR), and "today" is today's date in India.

## Limits
- Invoices: Excel .xlsx only. Contracts: PDF and Word only, not scanned images.
- One currency (rupees). No user accounts or logins yet, and no editing of invoices or contracts \
inside the app.

## Where things are
The left menu has: Home; Contracts (Dashboard, All contracts, Upload contract); Invoices \
(Dashboard, All invoices, Upload invoices); and Talk to Me. In-app links to use in answers: \
[Contracts dashboard](/contracts/dashboard), [All contracts](/contracts), \
[Upload a contract](/contracts/upload), [Invoices dashboard](/invoices/dashboard), \
[All invoices](/invoices), [Upload invoices](/invoices/upload), \
[Overdue invoices](/invoices?view=outstanding).
"""


def build_guide(invoice_days: int, contract_days: int) -> str:
    return _GUIDE.format(
        summary=APP_SUMMARY, invoice_days=invoice_days, contract_days=contract_days
    )
