"""CON-002 list and CON-003 dashboard, with "today" pinned to 25 Sep 2026."""

from datetime import date, timedelta
from urllib.parse import urlencode

import pytest

from app.extraction.base import ExtractionFailed
from app.extraction.schema import ContractExtraction, Party, Risk
from tests.contracts.conftest import TODAY, upload, wait_for_pipeline
from tests.contracts.documents import contract_docx


def d(offset: int) -> date:
    return TODAY + timedelta(days=offset)


def contract(title, parties, start, end, high=0, medium=0):
    risks = [
        Risk(severity="high", title=f"H{i}", description="d", source_text="q") for i in range(high)
    ]
    risks += [
        Risk(severity="medium", title=f"M{i}", description="d", source_text="q")
        for i in range(medium)
    ]
    return ContractExtraction(
        title=title,
        summary="s",
        parties=[Party(name=p, role="Party") for p in parties],
        start_date=start,
        end_date=end,
        key_dates=[],
        terms=[],
        risks=risks,
    )


PORTFOLIO = {
    "a.docx": contract(
        "Alpha Services", ["Kaveri Agro Foods", "Bluewave Logistics LLP"], d(-300), d(2)
    ),  # in force, expiring soon → at risk
    "b.docx": contract(
        "Beta Supply", ["Sharma Textiles"], d(-30), d(100), high=2
    ),  # high → at risk
    "c.docx": contract("Gamma Lease", ["Nilgiri Estates"], d(-400), d(-5), high=1),  # expired
    "d.docx": contract("Delta Retainer", ["Mehta Auto"], d(10), d(400), medium=1),  # not started
    "e.docx": contract("Echo Licence", ["Green Leaf Organics"], d(-50), None),  # no end date
}


@pytest.fixture
def portfolio(api, extractor):
    for name, data in PORTFOLIO.items():
        extractor.on(name, data)
        assert upload(api, contract_docx(unique=name), name).status_code == 202
    extractor.on("f.docx", ExtractionFailed("down"))
    upload(api, contract_docx(unique="f"), "f.docx")
    wait_for_pipeline(api)
    return api


def get_list(client, **params):
    response = client.get(f"/api/contracts?{urlencode(params)}")
    assert response.status_code == 200, response.text
    return response.json()


def titles(body):
    return [item["title"] for item in body["items"]]


# --- CON-002 --------------------------------------------------------------------------------


def test_CON_002_AC2_counts_per_view(portfolio):
    body = get_list(portfolio)

    assert body["counts"] == {
        "all": 5,
        "in_force": 2,
        "at_risk": 2,
        "not_started": 1,
        "expired": 1,
        "no_end_date": 1,
        "processing": 0,
        "failed": 1,
    }
    assert body["total"] == 5


def test_CON_002_AC3_default_order_is_soonest_end_date_first_no_end_date_last(portfolio):
    assert titles(get_list(portfolio)) == [
        "Gamma Lease",
        "Alpha Services",
        "Beta Supply",
        "Delta Retainer",
        "Echo Licence",
    ]


@pytest.mark.parametrize(
    ("view", "expected"),
    [
        ("in_force", {"Alpha Services", "Beta Supply"}),
        ("at_risk", {"Alpha Services", "Beta Supply"}),
        ("expired", {"Gamma Lease"}),
        ("not_started", {"Delta Retainer"}),
        ("no_end_date", {"Echo Licence"}),
        ("failed", {"f.docx"}),  # unread contracts show their file name
    ],
)
def test_CON_002_AC2_each_view_lists_its_contracts(portfolio, view, expected):
    assert set(titles(get_list(portfolio, view=view))) == expected


def test_CON_002_AC1_AC4_items_carry_status_reasons_and_parties(portfolio):
    items = {item["title"]: item for item in get_list(portfolio)["items"]}

    alpha = items["Alpha Services"]
    assert alpha["parties"] == ["Kaveri Agro Foods", "Bluewave Logistics LLP"]
    assert alpha["lifecycle"] == "in_force"
    assert alpha["at_risk_reasons"] == ["Expires in 2 days"]
    assert alpha["days_until_end"] == 2
    assert items["Beta Supply"]["at_risk_reasons"] == ["2 high risks"]
    assert items["Beta Supply"]["high_risk_count"] == 2
    assert items["Gamma Lease"]["at_risk"] is False  # expired is never at risk
    assert items["Delta Retainer"]["lifecycle"] == "not_started"


def test_CON_002_AC2_search_by_title_or_party(portfolio):
    assert titles(get_list(portfolio, q="bluewave")) == ["Alpha Services"]
    assert titles(get_list(portfolio, q="LEASE")) == ["Gamma Lease"]
    assert get_list(portfolio, q="bluewave")["counts"]["all"] == 1
    assert get_list(portfolio, q="100%_x")["total"] == 0


@pytest.mark.parametrize(
    ("sort", "order", "first"),
    [
        ("title", "asc", "Alpha Services"),
        ("title", "desc", "Gamma Lease"),
        ("start_date", "asc", "Gamma Lease"),
        ("high_risks", "desc", "Beta Supply"),
        ("status", "asc", "Alpha Services"),  # in force first
        ("end_date", "desc", "Delta Retainer"),  # no end date still last
    ],
)
def test_CON_002_AC3_every_column_sorts(portfolio, sort, order, first):
    body = get_list(portfolio, sort=sort, order=order)
    assert titles(body)[0] == first
    if sort == "end_date":
        assert titles(body)[-1] == "Echo Licence"


def test_CON_002_AC5_detail_groups_terms_and_orders_risks(api, extractor):
    from tests.contracts.test_upload_and_pipeline import extraction

    extractor.on("s.docx", extraction())
    contract_id = upload(api, contract_docx(), "s.docx").json()["id"]
    wait_for_pipeline(api)

    body = api.get(f"/api/contracts/{contract_id}").json()

    assert [t["category"] for t in body["terms"]] == ["payment", "confidentiality"]
    assert body["key_dates"][0]["days_from_today"] == (date(2026, 4, 1) - TODAY).days


# --- CON-003 --------------------------------------------------------------------------------


def dashboard(client):
    response = client.get("/api/contracts/dashboard")
    assert response.status_code == 200, response.text
    return response.json()


def test_CON_003_AC7_no_contracts_means_no_data(api):
    assert dashboard(api) == {"today": "2026-09-25", "has_data": False}


def test_CON_003_AC1_AC2_counts_only_read_contracts(portfolio):
    body = dashboard(portfolio)

    assert body["counts"] == {
        "total": 5,
        "in_force": 2,
        "at_risk": 2,
        "expired": 1,
        "not_started": 1,
        "no_end_date": 1,
    }
    partition = sum(item["count"] for item in body["by_lifecycle"])
    assert partition == body["counts"]["total"]
    assert [item["lifecycle"] for item in body["by_lifecycle"]] == [
        "in_force",
        "not_started",
        "no_end_date",
        "expired",
    ]


def test_CON_003_AC1a_at_risk_breakdown(portfolio):
    assert dashboard(portfolio)["at_risk_breakdown"] == {"expiring_soon": 1, "high_risk": 1}


def test_CON_003_AC3_every_card_link_returns_exactly_its_number(portfolio):
    body = dashboard(portfolio)
    card_for_link = {
        "total": "total",
        "in_force": "in_force",
        "at_risk": "at_risk",
        "expired": "expired",
        "not_started": "not_started",
        "no_end_date": "no_end_date",
    }

    for link, card in card_for_link.items():
        listed = get_list(portfolio, **body["links"][link])
        assert listed["total"] == body["counts"][card], link
    assert get_list(portfolio, **body["links"]["failed"])["total"] == body["unread"]["failed"]


def test_CON_003_AC4_needs_attention_puts_at_risk_first_then_soonest_end(portfolio):
    items = dashboard(portfolio)["needs_attention"]

    assert [item["title"] for item in items] == [
        "Alpha Services",
        "Beta Supply",
        "Delta Retainer",
        "Echo Licence",
    ]
    assert items[0]["at_risk_reasons"] == ["Expires in 2 days"]


def test_CON_003_AC6_unread_contracts_are_counted_separately(portfolio):
    assert dashboard(portfolio)["unread"] == {"processing": 0, "failed": 1}


def test_CON_003_AC8_dashboard_reports_the_date_it_used(portfolio):
    assert dashboard(portfolio)["today"] == "2026-09-25"
