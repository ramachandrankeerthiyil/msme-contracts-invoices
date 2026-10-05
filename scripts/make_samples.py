"""Generate demo files in samples/ (INV-001 task 16, plus two contracts for CON-001).

All companies and people are fictional. Dates are computed relative to the day the script runs,
so each file always demonstrates the intended statuses:

  samples/invoices-sample.xlsx       paid, outstanding (overdue), at risk, open — all valid rows, with emails
  samples/invoices-with-errors.xlsx  invalid rows + a duplicate invoice number (tests validation)
  samples/contract-msa-bluewave.docx services agreement: expires in 2 days, high-severity risks
  samples/contract-supply-sharma.docx supply agreement: in force until next year, balanced terms

Run (no local Python packages needed):
  docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work python:3.12-slim \
    sh -c "pip install -q --target /tmp/py openpyxl python-docx && PYTHONPATH=/tmp/py python scripts/make_samples.py"
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUT = Path(__file__).resolve().parent.parent / "samples"
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).date()
HEADERS = ["Invoice Number", "Customer Name", "Date Raised", "Due Date", "Amount", "Paid Date"]
# The sample adds the optional Customer Email column (INV-001 AC13). invoices-with-errors.xlsx keeps
# the six-column layout on purpose, so a sheet without the column stays covered.
SAMPLE_HEADERS = [*HEADERS, "Customer Email"]


def d(days: int) -> date:
    return TODAY + timedelta(days=days)


def long_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


# --------------------------------------------------------------------------------------------
# Invoices
# --------------------------------------------------------------------------------------------

# (number, customer, raised offset, due offset, amount, paid offset or None, expected status)
INVOICES = [
    # Paid
    ("INV-2601", "Sharma Textiles Pvt Ltd", -75, -45, 185000.00, -50, "Paid (early)"),
    ("INV-2602", "Kaveri Agro Foods", -60, -30, 42750.50, -28, "Paid (2 days late)"),
    ("INV-2603", "Bluewave Logistics LLP", -40, -10, 96400.00, -12, "Paid"),
    ("INV-2604", "Mehta Auto Components", -20, 10, 310000.00, -2, "Paid before due date"),
    ("INV-2605", "Green Leaf Organics", -15, 2, 18500.00, -1, "Paid (due soon, but paid)"),
    # Outstanding (unpaid and past due)
    ("INV-2606", "Deccan Printing Works", -70, -40, 125000.00, None, "Outstanding — 40 days overdue"),
    ("INV-2607", "Sunrise Pharma Distributors", -45, -15, 267500.75, None, "Outstanding — 15 days overdue"),
    ("INV-2608", "Nilgiri Tea Traders", -35, -5, 54000.00, None, "Outstanding — 5 days overdue"),
    ("INV-2609", "Kaveri Agro Foods", -31, -1, 8900.00, None, "Outstanding — 1 day overdue"),
    # At risk (unpaid, due within 5 days)
    ("INV-2610", "Mehta Auto Components", -30, 0, 142000.00, None, "At risk — due today"),
    ("INV-2611", "Bluewave Logistics LLP", -28, 1, 76250.00, None, "At risk — due tomorrow"),
    ("INV-2612", "Sharma Textiles Pvt Ltd", -27, 3, 225000.00, None, "At risk — due in 3 days"),
    ("INV-2613", "Green Leaf Organics", -25, 5, 31500.00, None, "At risk — due in 5 days"),
    # Open (unpaid, due later)
    ("INV-2614", "Deccan Printing Works", -20, 6, 64000.00, None, "Open — due in 6 days (this week)"),
    ("INV-2615", "Sunrise Pharma Distributors", -10, 20, 410000.00, None, "Open — due in 20 days"),
    ("INV-2616", "Nilgiri Tea Traders", -5, 25, 22800.00, None, "Open — due in 25 days"),
    ("INV-2617", "Kaveri Agro Foods", -2, 45, 98000.00, None, "Open — due in 45 days"),
]


# Invented, reserved ".example" addresses (INV-004). Nilgiri Tea Traders has none, so its
# outstanding invoice shows the "no email address on file" message.
CUSTOMER_EMAILS = {
    "Sharma Textiles Pvt Ltd": "accounts@sharmatextiles.example",
    "Kaveri Agro Foods": "payables@kaveriagro.example",
    "Bluewave Logistics LLP": "ap@bluewavelogistics.example",
    "Mehta Auto Components": "accounts@mehtaauto.example",
    "Green Leaf Organics": "finance@greenleaf.example",
    "Deccan Printing Works": "accounts@deccanprinting.example",
    "Sunrise Pharma Distributors": "ap@sunrisepharma.example",
}


def _style_sheet(ws, widths: list[int]) -> None:
    fill = PatternFill("solid", fgColor="D6E8F9")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="0F2742")
        cell.fill = fill
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    for column, width in zip("ABCDEFGH", widths, strict=False):
        ws.column_dimensions[column].width = width


def _format_row(ws, row: int) -> None:
    for column in "CDF":
        ws[f"{column}{row}"].number_format = "DD-MMM-YYYY"
    ws[f"E{row}"].number_format = "#,##,##0.00"


def make_invoices_sample() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(SAMPLE_HEADERS)
    for number, customer, raised, due, amount, paid, _status in INVOICES:
        ws.append(
            [
                number,
                customer,
                d(raised),
                d(due),
                amount,
                d(paid) if paid is not None else None,
                CUSTOMER_EMAILS.get(customer),
            ]
        )
        _format_row(ws, ws.max_row)
    _style_sheet(ws, [16, 32, 15, 15, 15, 15, 36])

    key = wb.create_sheet("Expected status")
    key.append(["Invoice Number", "Expected status (as of the day this file was generated)"])
    for number, *_rest, status in INVOICES:
        key.append([number, status])
    key.append([])
    key.append([f"Generated on {long_date(TODAY)}. Only the first sheet is read on upload."])
    _style_sheet(key, [16, 60])

    path = OUT / "invoices-sample.xlsx"
    wb.save(path)
    return path


def make_invoices_with_errors() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(HEADERS)
    rows = [
        ["INV-2701", "Sharma Textiles Pvt Ltd", d(-10), d(20), 50000, None],  # valid
        ["INV-2702", "", d(-10), d(20), 12000, None],  # missing customer
        ["INV-2703", "Kaveri Agro Foods", d(-5), d(-10), 8000, None],  # due before raised
        ["INV-2704", "Bluewave Logistics LLP", d(-5), d(25), -1500, None],  # negative amount
        ["INV-2705", "Green Leaf Organics", "31/13/2026", d(25), 9999, None],  # invalid date
        ["INV-2706", "Mehta Auto Components", d(-3), d(27), "12,500.00", None],  # valid (text amount)
        ["INV-2701", "Sharma Textiles Pvt Ltd", d(-10), d(20), 55000, None],  # duplicate: replaces row 2
        ["INV-2707", "Nilgiri Tea Traders", d(-4), d(2), 12500.555, None],  # 3 decimal places
    ]
    for row in rows:
        ws.append(row)
        _format_row(ws, ws.max_row)
    _style_sheet(ws, [16, 32, 15, 15, 15, 15])

    notes = wb.create_sheet("What to expect")
    notes.append(["Row", "Expected result"])
    for row, text in [
        (2, "Replaced by row 8 (same invoice number) — amount becomes 55,000"),
        (3, "Rejected: Customer Name is missing"),
        (4, "Rejected: Due Date is before Date Raised"),
        (5, "Rejected: Amount must be greater than zero"),
        (6, "Rejected: Date Raised '31/13/2026' is not a valid date"),
        (7, "Saved: amount given as text '12,500.00' is accepted"),
        (8, "Saved: overwrites row 2 (marked 'Updated')"),
        (9, "Rejected: Amount can have at most 2 decimal places"),
    ]:
        notes.append([row, text])
    _style_sheet(notes, [8, 70])

    path = OUT / "invoices-with-errors.xlsx"
    wb.save(path)
    return path


# --------------------------------------------------------------------------------------------
# Contracts
# --------------------------------------------------------------------------------------------


def _new_document(title: str) -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    heading = doc.add_heading(title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return doc


def _clauses(doc: Document, clauses: list[tuple[str, list[str]]]) -> None:
    for number, (heading, paragraphs) in enumerate(clauses, start=1):
        doc.add_heading(f"{number}. {heading}", level=2)
        for text in paragraphs:
            doc.add_paragraph(text)


def _signatures(doc: Document, parties: list[tuple[str, str, str]]) -> None:
    doc.add_heading("Signatures", level=2)
    table = doc.add_table(rows=1, cols=len(parties))
    for cell, (company, person, role) in zip(table.rows[0].cells, parties, strict=True):
        cell.text = f"For {company}\n\n\n______________________\n{person}\n{role}"


def make_msa_contract() -> Path:
    start = d(-358)
    end = d(2)  # expires within 3 days → "At risk"
    doc = _new_document("Master Services Agreement")
    doc.add_paragraph(
        f"This Master Services Agreement (the \"Agreement\") is entered into on {long_date(start)} "
        f"(the \"Effective Date\") between:"
    )
    doc.add_paragraph(
        "Kaveri Agro Foods Private Limited, a company incorporated under the Companies Act, 2013, "
        "having its registered office at 14 Industrial Estate, Mysuru, Karnataka 570016 "
        "(the \"Client\"); and",
        style="List Bullet",
    )
    doc.add_paragraph(
        "Bluewave Logistics LLP, a limited liability partnership having its office at "
        "Plot 22, Whitefield, Bengaluru, Karnataka 560066 (the \"Service Provider\").",
        style="List Bullet",
    )
    _clauses(
        doc,
        [
            ("Services", [
                "The Service Provider shall provide cold-chain transport and warehousing services "
                "for the Client's packaged food products across Karnataka and Tamil Nadu, as described "
                "in Schedule A.",
            ]),
            ("Term", [
                f"This Agreement commences on {long_date(start)} and shall remain in force until "
                f"{long_date(end)} (the \"Expiry Date\"), unless terminated earlier in accordance with "
                "Clause 7.",
                "This Agreement shall automatically renew for successive periods of two (2) years unless "
                "the Client gives written notice of non-renewal at least ninety (90) days before the "
                "Expiry Date.",
            ]),
            ("Fees and Payment", [
                "The Client shall pay the fees set out in Schedule B. The Service Provider shall invoice "
                "monthly in arrears. Invoices are payable within sixty (60) days of receipt.",
                "Late payments shall attract interest at 24% per annum, compounded monthly.",
                "The Service Provider may revise its fees by up to 15% once every six months by giving "
                "fifteen (15) days' written notice.",
            ]),
            ("Service Levels", [
                "The Service Provider shall use reasonable endeavours to maintain product temperatures "
                "between 2°C and 8°C. No service credits or penalties shall apply for any failure to "
                "meet these service levels.",
            ]),
            ("Liability and Indemnity", [
                "The Client shall indemnify the Service Provider against all losses, claims and expenses "
                "of any kind arising in connection with this Agreement, without limit.",
                "The Service Provider's total liability under this Agreement shall not exceed the fees "
                "paid in the one (1) month preceding the claim. The Service Provider shall not be liable "
                "for spoilage of goods in transit.",
            ]),
            ("Confidentiality", [
                "Each party shall keep confidential all information received from the other party and "
                "shall not disclose it to any third party without prior written consent.",
            ]),
            ("Termination", [
                "The Service Provider may terminate this Agreement at any time by giving seven (7) days' "
                "written notice. The Client may terminate only for material breach that remains "
                "unremedied for ninety (90) days after written notice.",
            ]),
            ("Exclusivity", [
                "During the term, the Client shall not engage any other logistics provider for the "
                "services described in Schedule A.",
            ]),
            ("Governing Law and Disputes", [
                "This Agreement is governed by the laws of India. Disputes shall be referred to "
                "arbitration by a sole arbitrator appointed by the Service Provider, seated in Bengaluru.",
            ]),
        ],
    )
    _signatures(doc, [
        ("Kaveri Agro Foods Private Limited", "Ananya Rao", "Director"),
        ("Bluewave Logistics LLP", "Vikram Nair", "Designated Partner"),
    ])
    path = OUT / "contract-msa-bluewave.docx"
    doc.save(path)
    return path


def make_supply_contract() -> Path:
    start = d(-176)
    end = d(189)  # in force, not expiring soon
    doc = _new_document("Supply Agreement")
    doc.add_paragraph(
        f"This Supply Agreement is made on {long_date(start)} between:"
    )
    doc.add_paragraph(
        "Sharma Textiles Private Limited, having its registered office at 7 Mill Road, "
        "Tiruppur, Tamil Nadu 641604 (the \"Supplier\"); and",
        style="List Bullet",
    )
    doc.add_paragraph(
        "Deccan Printing Works, a proprietorship firm having its place of business at "
        "45 Begumpet, Hyderabad, Telangana 500016 (the \"Buyer\").",
        style="List Bullet",
    )
    _clauses(
        doc,
        [
            ("Supply of Goods", [
                "The Supplier shall supply printed cotton fabric to the Buyer in accordance with purchase "
                "orders issued by the Buyer from time to time, at the prices listed in Annexure 1.",
            ]),
            ("Term", [
                f"This Agreement is effective from {long_date(start)} and shall continue until "
                f"{long_date(end)}. The parties may renew it by mutual written agreement at least "
                "thirty (30) days before expiry.",
            ]),
            ("Price and Payment", [
                "Prices are fixed for the term of this Agreement and are exclusive of GST, which shall be "
                "charged at the applicable rate.",
                "The Buyer shall pay each invoice within thirty (30) days of the invoice date by bank "
                "transfer. Late payments shall attract simple interest at 12% per annum.",
            ]),
            ("Delivery and Inspection", [
                "Goods shall be delivered to the Buyer's Hyderabad premises within fourteen (14) days of "
                "each purchase order. The Buyer may inspect goods within seven (7) days of delivery and "
                "reject any goods that do not meet the agreed specifications.",
            ]),
            ("Warranty", [
                "The Supplier warrants that all goods shall be free from defects in material and "
                "workmanship for ninety (90) days from delivery. Defective goods shall be replaced free "
                "of charge.",
            ]),
            ("Limitation of Liability", [
                "Neither party shall be liable for indirect or consequential losses. Each party's total "
                "liability under this Agreement shall not exceed the total value of goods supplied in the "
                "twelve (12) months preceding the claim.",
            ]),
            ("Confidentiality", [
                "Each party shall keep confidential the other party's pricing, designs and business "
                "information for the term of this Agreement and two (2) years afterwards.",
            ]),
            ("Termination", [
                "Either party may terminate this Agreement by giving thirty (30) days' written notice, or "
                "immediately if the other party commits a material breach that is not remedied within "
                "fifteen (15) days of written notice.",
            ]),
            ("Force Majeure", [
                "Neither party shall be liable for delay caused by events beyond its reasonable control, "
                "provided it notifies the other party promptly.",
            ]),
            ("Governing Law and Disputes", [
                "This Agreement is governed by the laws of India. Disputes shall first be discussed in good "
                "faith and, failing resolution within thirty (30) days, referred to arbitration by a sole "
                "arbitrator appointed jointly by the parties, seated in Hyderabad.",
            ]),
        ],
    )
    _signatures(doc, [
        ("Sharma Textiles Private Limited", "Rohit Sharma", "Managing Director"),
        ("Deccan Printing Works", "Farah Siddiqui", "Proprietor"),
    ])
    path = OUT / "contract-supply-sharma.docx"
    doc.save(path)
    return path


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for make in (make_invoices_sample, make_invoices_with_errors, make_msa_contract, make_supply_contract):
        print(f"wrote {make().relative_to(OUT.parent)}")
    print(f"dates relative to {TODAY.isoformat()} (Asia/Kolkata)")
