"""AST-001 AC14: what is logged and measured, and that question/answer text never is."""

from tests.conftest import BLUEWAVE_ID

QUESTION = "Which invoices does Deccan Printing Works still owe me? zebra-marker-question"
ANSWER = "Deccan owes you ₹2,50,000.00 — zebra-marker-answer"


def test_AST_001_AC14_logs_describe_the_answer_without_its_text(ask, use_model, logs):
    use_model(
        [("search_invoices", {"view": "unpaid", "search": "Deccan", "due_from": None,
                              "due_to": None, "sort": "amount", "order": "desc", "limit": 5}),
         ("get_contract_details", {"contract_id": BLUEWAVE_ID})],
        ANSWER,
    )

    ask(QUESTION, **{"X-Request-ID": "log-test-12345"})

    lines = logs()
    everything = "\n".join(str(line) for line in lines)
    assert "zebra-marker" not in everything
    assert "Deccan" not in everything  # not even the search text the model chose

    started = next(line for line in lines if line["event"] == "assistant_chat.started")
    assert started["turns"] == 1
    assert started["question_chars"] == len(QUESTION)

    tools = [line for line in lines if line["event"] == "assistant_tool.called"]
    assert {t["tool"] for t in tools} == {"search_invoices", "get_contract_details"}
    assert all(t["ok"] and t["duration_ms"] >= 0 for t in tools)

    completed = next(line for line in lines if line["event"] == "assistant_chat.completed")
    assert completed["request_id"] == "log-test-12345"
    assert completed["steps"] == 2
    assert sorted(completed["tools"]) == ["get_contract_details", "search_invoices"]
    assert completed["input_tokens"] == 200
    assert completed["output_tokens"] == 20
    assert completed["cache_read_tokens"] == 100
    assert completed["first_text_ms"] is not None
    assert completed["stop_reason"] == "end_turn"


def test_AST_001_AC14_metrics_count_chats_lookups_and_tokens(client, ask, use_model):
    use_model([("get_contract_overview", {})], "Two contracts.")
    ask("How many contracts?")

    metrics = client.get("/metrics").text

    assert 'assistant_chats_total{result="completed"}' in metrics
    assert 'assistant_tool_calls_total{ok="true",tool="get_contract_overview"}' in metrics
    assert "assistant_first_text_seconds_count" in metrics
    assert 'llm_tokens_total{direction="input",model="scripted"}' in metrics
