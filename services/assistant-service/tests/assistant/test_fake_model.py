"""The deterministic fake model (ASSISTANT_LLM=fake) that e2e tests run against."""

from tests.conftest import BLUEWAVE_ID, answer_text


def _labels(events):
    return [d["label"] for kind, d in events if kind == "status" and d["state"] != "running"]


def test_unpaid_question_lists_every_unpaid_invoice_with_links(ask):
    events = ask("Which invoices are unpaid as of today?")

    text = answer_text(events)
    assert _labels(events) == ["Checked unpaid invoices"]
    assert "**3 invoices** worth **₹14,89,067.50**" in text
    assert "[INV-2606](/invoices?view=all&q=INV-2606)" in text
    assert "16 Aug 2026 (40 days overdue)" in text
    assert "INV-2590" not in text  # paid
    assert events[-1] == ("done", {"stop_reason": "end_turn"})


def test_contract_risk_question_searches_then_reads_the_contract(ask):
    events = ask("What risks are in the Bluewave contract?")

    text = answer_text(events)
    assert _labels(events) == ["Checked contracts", "Read “Master Services Agreement”"]
    assert f"[Master Services Agreement](/contracts/{BLUEWAVE_ID})" in text
    assert "**High:** Unlimited liability" in text
    assert "not legal advice" in text


def test_contract_summary_question_uses_the_dashboard(ask):
    events = ask("How many contracts do I have?")

    assert _labels(events) == ["Checked the contract dashboard"]
    assert "**2 contracts**" in answer_text(events)


def test_AST_001_AC10_write_requests_are_declined_without_lookups(ask, downstream):
    events = ask("Please mark INV-2606 as paid")

    assert downstream.requests == []
    assert "can't change anything" in answer_text(events)


def test_AST_001_AC10_unrelated_questions_are_declined(ask, downstream):
    events = ask("What's the weather in Chennai?")

    assert downstream.requests == []
    assert "contracts and invoices" in answer_text(events)


def test_failed_lookup_is_explained(ask, downstream):
    downstream.fail.add("invoice")

    events = ask("Which invoices are unpaid?")

    assert "couldn't check" in answer_text(events)
