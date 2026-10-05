"""The Claude request (without calling the API), tool definitions and presentation helpers."""

import asyncio

import pytest

from app.assistant.claude import MAX_TOKENS, ClaudeModel
from app.assistant.events import AssistantError
from app.assistant.prompt import INSTRUCTIONS, build_system
from app.assistant.tools import TOOL_DEFINITIONS, TOOL_NAMES, format_inr, lookup_labels
from app.config import Settings
from app.main import build_model
from tests.conftest import TODAY


def test_request_uses_sonnet_5_adaptive_thinking_and_caching():
    model = ClaudeModel(api_key="test", model="claude-sonnet-5", effort="medium")

    params = model.request_params(
        system=build_system(TODAY, "Asia/Kolkata"), tools=TOOL_DEFINITIONS, messages=[]
    )

    assert params["model"] == "claude-sonnet-5"
    assert params["max_tokens"] == MAX_TOKENS == 4000
    assert params["thinking"] == {"type": "adaptive"}
    assert params["output_config"] == {"effort": "medium"}
    assert params["cache_control"] == {"type": "ephemeral"}
    assert params["system"][0]["text"] == INSTRUCTIONS
    assert params["system"][2]["text"] == "Today is Friday, 25 Sep 2026 (Asia/Kolkata)."


def test_default_settings_choose_claude_sonnet_5():
    settings = Settings(_env_file=None, anthropic_api_key="k", assistant_llm="claude")

    model = build_model(settings)

    assert isinstance(model, ClaudeModel)
    assert model.model == "claude-sonnet-5"


def test_AST_001_AC12_no_api_key_fails_before_any_call():
    model = ClaudeModel(api_key="", model="claude-sonnet-5", effort="medium")

    async def first():
        return await anext(model.stream_step(system=[], tools=[], messages=[]))

    with pytest.raises(AssistantError) as caught:
        asyncio.run(first())
    assert caught.value.code == "AI_NOT_CONFIGURED"


def test_AST_001_AC10_tools_are_the_five_read_only_lookups():
    assert TOOL_NAMES == [
        "get_invoice_overview",
        "search_invoices",
        "get_contract_overview",
        "search_contracts",
        "get_contract_details",
    ]
    for tool in TOOL_DEFINITIONS:
        schema = tool["input_schema"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert sorted(schema.get("required", [])) == sorted(schema["properties"])


def test_AST_001_AC9_prompt_sets_the_house_rules():
    for rule in ("₹", "24 Sep 2026", "link", "legal advice", "data", "cannot change"):
        assert rule in INSTRUCTIONS


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "₹0.00"),
        ("999", "₹999.00"),
        ("1000", "₹1,000.00"),
        ("425000", "₹4,25,000.00"),
        ("994150.75", "₹9,94,150.75"),
        ("12345678.9", "₹1,23,45,678.90"),
        ("-1500", "-₹1,500.00"),
        (None, None),
        ("abc", None),
    ],
)
def test_AST_001_AC9_amounts_use_indian_grouping(value, expected):
    assert format_inr(value) == expected


@pytest.mark.parametrize(
    ("name", "tool_input", "running"),
    [
        ("search_invoices", {"view": "outstanding"}, "Checking overdue invoices"),
        ("search_invoices", {"view": "all", "search": "Kaveri"}, "Checking invoices matching “Kaveri”"),  # noqa: E501
        ("search_contracts", {"view": "expired"}, "Checking expired contracts"),
        ("get_invoice_overview", {}, "Checking the invoice dashboard"),
        ("get_contract_details", {"contract_id": "x"}, "Reading the contract"),
    ],
)
def test_AST_001_AC6_lookup_labels_are_fixed_wording(name, tool_input, running):
    assert lookup_labels(name, tool_input)[0] == running
