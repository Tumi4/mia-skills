"""Tests for the MIA agent service.

NO TEST HERE CALLS THE REAL ANTHROPIC API OR NEEDS A KEY. The Anthropic client
is always a fake that returns scripted responses; the gateway, by contrast, is
the REAL in-process gateway, because the whole point of the agent is that it
drives the live skills without a network hop - mocking that away would test
nothing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import (  # noqa: E402
    SYSTEM_PROMPT,
    AgentReply,
    MiaAgent,
    MissingAPIKeyError,
    TurnLimitError,
    human_items,
    load_gateway,
    to_anthropic_tools,
)

# ─── Fake Anthropic client ──────────────────────────────────────────────────────


@dataclass
class FakeText:
    text: str
    type: str = "text"


@dataclass
class FakeToolUse:
    name: str
    input: dict[str, Any]
    id: str = "toolu_test"
    type: str = "tool_use"


class FakeResponse:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    """Returns scripted responses in order and records every request."""

    def __init__(self, script):
        self._script = list(script)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self._script:
            return FakeResponse([FakeText("done")])
        return self._script.pop(0)


class FakeClient:
    def __init__(self, script):
        self.messages = FakeMessages(script)


def build_agent(script, **kwargs) -> MiaAgent:
    """An agent with a scripted model and the REAL in-process gateway."""
    return MiaAgent(client=FakeClient(script), gateway=load_gateway(), **kwargs)


# ─── Gateway tool discovery ─────────────────────────────────────────────────────


class TestToolDiscovery:
    async def test_discovers_every_gateway_tool(self):
        """The agent sees exactly the gateway's live-skill tool surface.

        Pinned against the gateway itself rather than a hardcoded number, so a
        new live skill can never silently fail to reach the agent.
        """
        from fastmcp import Client

        gateway = load_gateway()
        async with Client(gateway) as mcp:
            expected = {t.name for t in await mcp.list_tools()}

        agent = build_agent([])
        tools = await agent.list_tools()

        assert {t["name"] for t in tools} == expected
        assert len(tools) == 27  # 26 live-skill tools + gateway_status

    async def test_tools_are_valid_anthropic_schemas(self):
        agent = build_agent([])
        for tool in await agent.list_tools():
            assert tool["name"]
            assert tool["description"]
            assert tool["input_schema"]["type"] == "object"

    def test_conversion_renames_mcp_fields(self):
        class T:
            name = "turnover_calculate_turnover_tax"
            description = "  Calculate turnover tax.  "
            inputSchema = {"type": "object", "properties": {}}  # noqa: N815

        converted = to_anthropic_tools([T()])
        assert converted == [
            {
                "name": "turnover_calculate_turnover_tax",
                "description": "Calculate turnover tax.",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]


# ─── The tool loop ──────────────────────────────────────────────────────────────


class TestToolLoop:
    async def test_multi_tool_turn(self):
        """The assistant may call several tools before answering.

        Two tools in one assistant turn, then a third in a second round trip,
        then the final text - all inside a single user turn.
        """
        agent = build_agent(
            [
                FakeResponse(
                    [
                        FakeText("Let me work both of those out."),
                        FakeToolUse(
                            "turnover_calculate_turnover_tax",
                            {"input": {"annual_turnover_zar": 1_000_000}},
                            id="t1",
                        ),
                        FakeToolUse(
                            "vat_check_registration_required",
                            {"input": {"rolling_12m_taxable_supplies_zar": 1_000_000}},
                            id="t2",
                        ),
                    ],
                    stop_reason="tool_use",
                ),
                FakeResponse(
                    [
                        FakeToolUse(
                            "sdl_check_sdl_liability",
                            {"input": {"expected_total_remuneration_next_12m_zar": 600_000}},
                            id="t3",
                        )
                    ],
                    stop_reason="tool_use",
                ),
                FakeResponse([FakeText("Turnover tax is R4,500.")]),
            ]
        )

        result = await agent.chat("s1", "Turnover tax and VAT on R1m?")

        assert result.tools_called == [
            "turnover_calculate_turnover_tax",
            "vat_check_registration_required",
            "sdl_check_sdl_liability",
        ]
        assert all(c.ok for c in result.calls)
        assert result.reply == "Turnover tax is R4,500."
        assert result.stopped_early is False

        # Real numbers came back through the real gateway, not from the model.
        turnover = result.calls[0].result
        assert turnover["turnover_tax_zar"] == 4_500.0

    async def test_requires_human_reaches_the_reply(self):
        """A requires_human field in a tool result must survive to the caller."""
        agent = build_agent(
            [
                FakeResponse(
                    [
                        FakeToolUse(
                            "s12b_calculate_deduction",
                            {
                                "input": {
                                    "equipment_cost_zar": 500_000,
                                    "taxable_income_zar": 2_000_000,
                                }
                            },
                            id="t1",
                        )
                    ],
                    stop_reason="tool_use",
                ),
                FakeResponse([FakeText("You would deduct R500,000.")]),
            ]
        )

        result = await agent.chat("s2", "R500k solar system, R2m taxable income?")

        assert result.calls[0].result["requires_human"] is True
        assert result.requires_human, "human steps must be surfaced, not swallowed"
        assert any("Certificate of Compliance" in step for step in result.requires_human)

    async def test_warnings_are_surfaced_too(self):
        """warnings ride the same honesty channel as human_steps."""
        agent = build_agent(
            [
                FakeResponse(
                    [
                        FakeToolUse(
                            "s12b_calculate_deduction",
                            {
                                "input": {
                                    "equipment_cost_zar": 1_000_000,
                                    "taxable_income_zar": 300_000,
                                    "taxpayer_type": "company",
                                }
                            },
                            id="t1",
                        )
                    ],
                    stop_reason="tool_use",
                ),
                FakeResponse([FakeText("The deduction exceeds your income.")]),
            ]
        )

        result = await agent.chat("s3", "R1m system but only R300k income?")

        assert any("assessed loss" in item.lower() for item in result.requires_human)

    async def test_tool_failure_is_reported_not_raised(self):
        """A failing tool comes back as an error result the model can react to."""
        agent = build_agent(
            [
                FakeResponse(
                    [FakeToolUse("turnover_calculate_turnover_tax", {"input": {}}, id="t1")],
                    stop_reason="tool_use",
                ),
                FakeResponse([FakeText("I need your annual turnover to work that out.")]),
            ]
        )

        result = await agent.chat("s4", "Turnover tax?")

        assert result.calls[0].ok is False
        assert result.calls[0].error
        assert "turnover" in result.reply.lower()

    async def test_iteration_cap_stops_a_runaway_turn(self):
        """The loop cap is a real cost guard, and says so rather than half-answering."""
        looping = [
            FakeResponse(
                [FakeToolUse("turnover_calculate_turnover_tax", {"input": {}}, id=f"t{i}")],
                stop_reason="tool_use",
            )
            for i in range(10)
        ]
        agent = build_agent(looping, max_tool_iterations=3)

        result = await agent.chat("s5", "loop please")

        assert result.stopped_early is True
        assert len(result.calls) == 3
        assert "single calculation" in result.reply

    async def test_no_tool_call_still_answers(self):
        agent = build_agent([FakeResponse([FakeText("I cover SA business tax calculations.")])])
        result = await agent.chat("s6", "hello")
        assert result.tools_called == []
        assert "SA business tax" in result.reply


# ─── Scope discipline ───────────────────────────────────────────────────────────


class TestScope:
    async def test_out_of_scope_question_is_declined(self):
        """An off-topic question is declined and redirected, with no tool call."""
        agent = build_agent(
            [
                FakeResponse(
                    [
                        FakeText(
                            "I can't help with that - I only handle South African business "
                            "tax, payroll and compliance calculations. Want me to work out "
                            "your turnover tax or VAT position instead?"
                        )
                    ]
                )
            ]
        )

        result = await agent.chat("s7", "Write me a Python web scraper.")

        assert result.tools_called == []
        assert "South African business" in result.reply

    async def test_refusal_stop_reason_is_handled(self):
        """A model refusal is a content outcome, not a crash."""
        agent = build_agent([FakeResponse([], stop_reason="refusal")])
        result = await agent.chat("s8", "something disallowed")
        assert "can't help" in result.reply
        assert result.tools_called == []

    def test_system_prompt_states_the_four_rules(self):
        """The prompt is the product - pin the load-bearing rules."""
        assert "NARROWLY SCOPED" in SYSTEM_PROMPT
        assert "NEVER state a rand figure" in SYSTEM_PROMPT
        assert "requires_human" in SYSTEM_PROMPT and "warnings" in SYSTEM_PROMPT
        assert "not tax advice" in SYSTEM_PROMPT

    async def test_system_prompt_is_sent_with_every_request(self):
        agent = build_agent([FakeResponse([FakeText("ok")])])
        await agent.chat("s9", "hi")
        assert agent.client.messages.requests[0]["system"] == SYSTEM_PROMPT


# ─── Cost guards and session state ──────────────────────────────────────────────


class TestGuards:
    async def test_turn_limit_per_session(self):
        agent = build_agent([FakeResponse([FakeText("ok")]) for _ in range(10)], max_turns=2)
        await agent.chat("s10", "one")
        await agent.chat("s10", "two")
        with pytest.raises(TurnLimitError):
            await agent.chat("s10", "three")

    async def test_turn_limit_is_per_session_not_global(self):
        agent = build_agent([FakeResponse([FakeText("ok")]) for _ in range(10)], max_turns=1)
        await agent.chat("a", "hi")
        await agent.chat("b", "hi")  # a different session is unaffected

    async def test_max_output_tokens_and_effort_are_passed_through(self):
        agent = build_agent([FakeResponse([FakeText("ok")])], max_output_tokens=1234, effort="low")
        await agent.chat("s11", "hi")
        request = agent.client.messages.requests[0]
        assert request["max_tokens"] == 1234
        assert request["output_config"] == {"effort": "low"}

    async def test_history_persists_across_turns(self):
        agent = build_agent([FakeResponse([FakeText("first")]), FakeResponse([FakeText("second")])])
        await agent.chat("s12", "one")
        await agent.chat("s12", "two")
        sent = agent.client.messages.requests[1]["messages"]
        assert sent[0]["content"] == "one"
        assert len(sent) >= 3

    async def test_reset_clears_a_session(self):
        agent = build_agent([FakeResponse([FakeText("ok")]) for _ in range(5)], max_turns=1)
        await agent.chat("s13", "hi")
        agent.reset("s13")
        await agent.chat("s13", "hi again")  # limit no longer tripped

    def test_missing_api_key_raises_a_typed_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        agent = MiaAgent(gateway=load_gateway())
        with pytest.raises(MissingAPIKeyError) as exc:
            _ = agent.client
        assert "ANTHROPIC_API_KEY" in str(exc.value)


# ─── Helpers ────────────────────────────────────────────────────────────────────


class TestHumanItems:
    def test_collects_steps_and_warnings(self):
        items = human_items(
            {
                "requires_human": True,
                "human_steps": ["Get a CoC", "Confirm with a practitioner"],
                "warnings": ["Deduction exceeds income"],
            }
        )
        assert items == ["Get a CoC", "Confirm with a practitioner", "Deduction exceeds income"]

    def test_clean_result_yields_nothing(self):
        assert human_items({"requires_human": False, "warnings": []}) == []

    def test_requires_human_without_steps_still_flags(self):
        assert human_items({"requires_human": True}) != []

    def test_warnings_surface_even_without_requires_human(self):
        assert human_items({"requires_human": False, "warnings": ["heads up"]}) == ["heads up"]


def test_agent_reply_defaults():
    reply = AgentReply(reply="hi")
    assert reply.tools_called == []
    assert reply.requires_human == []
    assert reply.stopped_early is False
