"""POST /api/assistant/chat: the SSE contract, the tool loop and its limits (AST-001)."""

import pytest

from app.assistant.events import AssistantError
from app.assistant.prompt import LIMIT_REACHED_NOTE
from tests.conftest import BLUEWAVE_ID, answer_text

UNPAID = {
    "view": "unpaid", "search": None, "due_from": None, "due_to": None,
    "sort": "due_date", "order": "asc", "limit": 50,
}


def test_AST_001_AC4_AC6_events_are_status_then_text_then_done(ask, use_model):
    use_model([("search_invoices", UNPAID)], "You have 3 unpaid invoices.")

    events = ask("Which invoices are unpaid as of today?")

    kinds = [kind for kind, _ in events]
    assert kinds == ["status", "status", "text", "text", "done"]
    assert events[0][1] == {"id": "t1", "state": "running", "label": "Checking unpaid invoices"}
    assert events[1][1] == {"id": "t1", "state": "done", "label": "Checked unpaid invoices",
                            "count": 3}
    assert answer_text(events) == "You have 3 unpaid invoices."
    assert events[-1][1] == {"stop_reason": "end_turn"}


def test_AST_001_AC5_AC7_unpaid_lookup_merges_views_and_builds_links(ask, use_model, downstream):
    model = use_model([("search_invoices", UNPAID)], "Done.")

    ask("Which invoices are unpaid?")

    views = sorted(r.url.params["view"] for r in downstream.requests)
    assert views == ["follow_up", "open"]
    [result] = model.tool_results(1)
    assert result["total"] == 3
    assert result["total_amount"] == "₹14,89,067.50"
    assert [i["invoice_number"] for i in result["invoices"]] == ["INV-2606", "INV-2611", "INV-2620"]
    first = result["invoices"][0]
    assert first["link"] == "/invoices?view=all&q=INV-2606"
    assert first["amount"] == "₹2,50,000.00"
    assert first["status"] == "Outstanding (overdue)"
    assert first["days_until_due"] == -40


def test_AST_001_AC5_parallel_lookups_run_and_return_in_one_message(ask, use_model, downstream):
    model = use_model(
        [("get_invoice_overview", {}), ("get_contract_overview", {})], "Here is a summary."
    )

    events = ask("How is my business doing?")

    done = [data for kind, data in events if kind == "status" and data["state"] == "done"]
    assert [d["label"] for d in done] == [
        "Checked the invoice dashboard", "Checked the contract dashboard"
    ]
    results = model.tool_results(1)
    assert len(results) == 2
    assert results[1]["needs_attention"][0]["link"] == f"/contracts/{BLUEWAVE_ID}"
    assert results[0]["top_to_chase"][0]["invoice_number"] == "INV-2606"


def test_AST_001_AC6_contract_details_label_names_the_contract(ask, use_model):
    model = use_model([("get_contract_details", {"contract_id": BLUEWAVE_ID})], "Two risks.")

    events = ask("What risks are in the Bluewave contract?")

    assert events[1][1]["label"] == "Read “Master Services Agreement”"
    assert events[1][1]["count"] == 2
    [result] = model.tool_results(1)
    assert [r["title"] for r in result["risks"]] == ["Unlimited liability", "Auto-renewal"]
    assert result["risks"][0]["quote"] == "liability shall be unlimited"
    assert result["parties"] == ["Bluewave Logistics (Service provider)", "Our Company (Customer)"]


def test_AST_001_AC5_failed_lookup_becomes_an_error_result_not_a_crash(
    ask, use_model, downstream
):
    downstream.fail.add("invoice")
    model = use_model([("search_invoices", UNPAID)], "I couldn't check your invoices.")

    events = ask("Which invoices are unpaid?")

    assert events[1][1]["state"] == "failed"
    assert events[1][1]["label"] == "Couldn't check unpaid invoices"
    [result] = model.tool_results(1)
    assert result["_is_error"] is True
    assert "invoice service" in result["error"]
    assert events[-1][0] == "done"


def test_AST_001_AC5_unreachable_service_is_reported_to_the_model(ask, use_model, downstream):
    downstream.unreachable.add("contract")
    model = use_model([("get_contract_overview", {})], "Sorry.")

    ask("How are my contracts?")

    assert model.tool_results(1)[0]["error"] == "The contract service could not be reached."


def test_AST_001_AC5_bad_contract_id_is_rejected_without_a_request(ask, use_model, downstream):
    model = use_model([("get_contract_details", {"contract_id": "../../invoices"})], "Sorry.")

    events = ask("Tell me about that contract")

    assert downstream.requests == []
    assert events[1][1] == {"id": "t1", "state": "failed", "label": "Couldn't read the contract"}
    assert model.tool_results(1)[0]["_is_error"] is True


def test_AST_001_AC15_at_most_eight_lookups_per_question(ask, use_model, downstream):
    five = [("get_invoice_overview", {})] * 5
    model = use_model(five, five, "Answer with what I have.")

    events = ask("Tell me everything")

    running = [d for kind, d in events if kind == "status" and d["state"] == "running"]
    assert len(running) == 8
    assert len([r for r in downstream.requests if r.url.path == "/api/invoices/dashboard"]) == 8
    second = model.seen[2][-1]["content"]
    refused = [
        b for b in second if b.get("type") == "tool_result" and LIMIT_REACHED_NOTE in b["content"]
    ]
    assert len(refused) == 2
    assert second[-1] == {"type": "text", "text": LIMIT_REACHED_NOTE}
    assert answer_text(events) == "Answer with what I have."


def test_AST_001_AC15_a_model_that_never_answers_ends_with_an_error(ask, use_model):
    use_model(*([[("get_contract_overview", {})]] * 20))

    events = ask("Loop forever", **{"X-Request-ID": "loop-test-1234"})

    assert events[-1] == (
        "error",
        {
            "code": "ASSISTANT_FAILED",
            "message": "Talk to Me couldn't answer that right now. Please try again in a moment.",
            "request_id": "loop-test-1234",
        },
    )


def test_AST_001_AC12_model_failure_gives_a_plain_error_event(ask, use_model, logs):
    use_model(AssistantError("ASSISTANT_FAILED", "OverloadedError: busy"))

    events = ask("Hello?", **{"X-Request-ID": "fail-test-1234"})

    assert events == [
        (
            "error",
            {
                "code": "ASSISTANT_FAILED",
                "message": AssistantError("ASSISTANT_FAILED", "").user_message,
                "request_id": "fail-test-1234",
            },
        )
    ]
    [failed] = [line for line in logs() if line["event"] == "assistant_chat.failed"]
    assert failed["reason"] == "OverloadedError: busy"
    assert failed["request_id"] == "fail-test-1234"


def test_AST_001_AC12_unexpected_bug_still_ends_the_stream_cleanly(ask, use_model):
    use_model(RuntimeError("boom"))

    events = ask("Hello?")

    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "ASSISTANT_FAILED"


def test_AST_001_AC12_missing_key_says_not_set_up(ask, use_model):
    use_model(AssistantError("AI_NOT_CONFIGURED", "ANTHROPIC_API_KEY is not set"))

    events = ask("Hello?")

    assert events[-1][1]["code"] == "AI_NOT_CONFIGURED"
    assert "isn't set up yet" in events[-1][1]["message"]


def test_AST_001_AC4_text_from_separate_steps_gets_its_own_paragraph(ask, use_model):
    model = use_model(("Let me check.", [("get_invoice_overview", {})]), "All good.")

    events = ask("How are my invoices?")

    assert answer_text(events) == "Let me check.\n\nAll good."
    kinds = [kind for kind, _ in events]
    assert kinds.index("status") > kinds.index("text")  # the lookup shows after the first words
    # The model's own step (text + tool_use) is replayed unchanged before the tool results.
    replayed = model.seen[1][-2]["content"]
    assert [b["type"] for b in replayed] == ["text", "tool_use"]


def test_AST_001_AC8_history_is_sent_to_the_model_as_is(ask, use_model):
    model = use_model("Kaveri Textiles.")
    history = [
        {"role": "user", "content": "Which invoices are unpaid?"},
        {"role": "assistant", "content": "You have 3 unpaid invoices."},
        {"role": "user", "content": "Which is the biggest?"},
    ]

    ask(history)

    assert model.seen[0] == history


@pytest.mark.parametrize(
    ("messages", "problem"),
    [
        ([], "at least 1"),
        ([{"role": "assistant", "content": "Hi"}], "alternate"),
        ([{"role": "user", "content": "a"}, {"role": "user", "content": "b"}], "alternate"),
        ([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}], "last"),
        ([{"role": "user", "content": "   "}], "blank"),
        ([{"role": "user", "content": "x" * 1001}], "1,000"),
        ([{"role": "system", "content": "x"}], "user"),
        (
            [{"role": "user", "content": "q"}, {"role": "assistant", "content": "x" * 8001},
             {"role": "user", "content": "q"}],
            "8,000",
        ),
        ([{"role": r, "content": "x"} for r in ["user", "assistant"] * 10 + ["user"]], "20"),
    ],
)
def test_AST_001_AC8_invalid_conversations_are_rejected(client, use_model, messages, problem):
    model = use_model("never")

    response = client.post("/api/assistant/chat", json={"messages": messages})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert problem in str(body["details"])
    assert model.seen == []


def test_AST_001_AC3_a_question_of_exactly_1000_characters_is_accepted(ask, use_model):
    use_model("Fine.")

    assert answer_text(ask("x" * 1000)) == "Fine."


def test_AST_001_AC10_lookups_only_ever_read(ask, use_model, downstream):
    use_model(
        [
            ("get_invoice_overview", {}),
            ("search_invoices", UNPAID),
            ("get_contract_overview", {}),
            ("search_contracts", {"view": "at_risk", "search": "blue", "sort": "end_date",
                                  "order": "asc", "limit": 5}),
            ("get_contract_details", {"contract_id": BLUEWAVE_ID}),
        ],
        "Done.",
    )

    ask("Everything please")

    assert downstream.requests
    assert {r.method for r in downstream.requests} == {"GET"}


def test_AST_001_AC14_request_id_is_passed_to_the_services(ask, use_model, downstream):
    use_model([("get_contract_overview", {})], "Done.")

    ask("Contracts?", **{"X-Request-ID": "trace-me-12345"})

    assert downstream.requests[0].headers["X-Request-ID"] == "trace-me-12345"
