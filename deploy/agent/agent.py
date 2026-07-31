"""
MIA agent core - an LLM wired to the live MIA skills, with no web framework.

This is a DEPLOYMENT artifact, not a skill. It is deliberately CHANNEL-AGNOSTIC:
nothing in this file knows about HTTP, WhatsApp, or Slack. It exposes one call -

    reply = await agent.chat(session_id, message)

- and every surface (the browser chat page in server.py today, a WhatsApp or
Slack webhook adapter tomorrow) is a thin adapter over that call.

How it reaches the skills:

    deploy/gateway/server.py  ->  gateway (FastMCP)  ->  fastmcp.Client(gateway)

The gateway is imported IN-PROCESS and driven over fastmcp's in-memory
transport. There is no network hop and no dependency on the deployed gateway
being up - same repo, same process, same live-skill surface.

Cost guards (every one env-overridable, see README):
    MIA_MAX_OUTPUT_TOKENS   max output tokens per model reply
    MIA_MAX_TOOL_ITERATIONS max model<->tool round trips in one turn
    MIA_MAX_TURNS           max user turns per session
    MIA_EFFORT              reasoning effort: low | medium | high | xhigh | max

Credentials: ANTHROPIC_API_KEY is read from the environment and never written
to disk. .env and .env.local are gitignored at the repo root.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from fastmcp import Client

logger = logging.getLogger("mia.agent")

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_SERVER = REPO_ROOT / "deploy" / "gateway" / "server.py"

# Model id. Deliberately env-driven and defined in exactly one place: model ids
# change, and a hardcoded id buried in the request call is the thing that rots.
DEFAULT_MODEL = "claude-opus-5"

# ─── Cost guards (all env-overridable) ──────────────────────────────────────────


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer - using default %s", name, raw, default)
        return default


MODEL = os.environ.get("MIA_MODEL", DEFAULT_MODEL)
MAX_OUTPUT_TOKENS = _env_int("MIA_MAX_OUTPUT_TOKENS", 4096)
MAX_TOOL_ITERATIONS = _env_int("MIA_MAX_TOOL_ITERATIONS", 6)
MAX_TURNS = _env_int("MIA_MAX_TURNS", 20)
EFFORT = os.environ.get("MIA_EFFORT", "medium")


# ─── The system prompt: this is the product ─────────────────────────────────────
#
# Four rules, each load-bearing:
#
# 1. NARROW SCOPE. This is not a general assistant. Meta's 2026 WhatsApp policy
#    permits task-scoped business assistants but bans general-purpose LLM
#    chatbots - a "MIA can chat about anything" bot would get a WhatsApp number
#    banned once that adapter ships. The scope limit is a business requirement,
#    not a stylistic one.
# 2. NEVER quote a number from model knowledge. Every rand figure, rate and
#    threshold must come out of a tool call, because only the tools are verified
#    against a primary source with a cited URL and check date.
# 3. PASS ON requires_human / human_steps / warnings verbatim. This is the
#    honesty contract in docs/integration.md - the calling agent must surface
#    them, not swallow them.
# 4. It is a CALCULATION, never tax advice.

SYSTEM_PROMPT = """You are MIA, an assistant for South African founders and business owners.

# What you do

You answer questions about South African business tax, payroll and compliance by
calling the calculation tools available to you. Those tools cover:

- Section 12B solar / renewable energy deductions
- Turnover tax (the micro-business regime)
- VAT registration thresholds and position
- PAYE (employees' tax)
- SDL (skills development levy)
- Carbon tax
- Provisional tax

# Scope - this matters

You are NARROWLY SCOPED to those topics. You are not a general-purpose assistant.

If someone asks you about anything else - general knowledge, coding, other
countries' tax systems, personal advice, current events, writing help, or simply
chatting - politely decline in one or two sentences and tell them what you DO
cover. Do not answer the off-topic question anyway, and do not answer "just this
once". Offer to help with a South African business tax, payroll or compliance
calculation instead.

# Numbers: tools only, never memory

NEVER state a rand figure, a tax rate, a bracket, a threshold or a percentage
from your own knowledge. Every single number you give must come from a tool call
you made in this conversation.

- If a question needs a number, call the tool that produces it.
- If no tool covers what was asked, say so plainly: tell the user this skill
  library does not cover that calculation yet, and do not estimate, approximate,
  or reason your way to a figure. A missing answer is correct; an invented number
  is not.
- If you are missing an input a tool requires, ask the user for it rather than
  assuming a value.

The tools are verified against SARS and National Treasury sources with the URL
and check date recorded in each skill. Your training data is not. That is the
whole reason this rule exists.

# Passing on what the tools tell you

When a tool result contains `requires_human`, `human_steps` or `warnings`, you
MUST pass every one of those items on to the user in your reply. Do not
summarise them away, do not drop the ones that seem minor, and do not bury them.
Most South African operational processes have at least one human step -
practitioner sign-off, a certificate, an in-person verification - and hiding
that would make the answer dishonest.

Also surface a tool's `notes` field when it adds context to the figures.

# How to answer

- Lead with the number the user asked for, then the supporting detail.
- Keep replies short and readable. Many users are on a phone.
- Use plain language, not tax jargon, and spell out what a figure means.
- Always make clear this is a CALCULATION, not tax advice, and that a registered
  tax practitioner should confirm anything before it is filed. Say it naturally
  once per answer - do not repeat it in every paragraph.
- If a tool call fails, say so honestly rather than guessing at the result.
"""


# ─── Errors ─────────────────────────────────────────────────────────────────────


class AgentError(Exception):
    """Base class for agent errors."""


class MissingAPIKeyError(AgentError):
    """ANTHROPIC_API_KEY is not set in the environment."""


class TurnLimitError(AgentError):
    """The session hit its per-session turn cap."""


# ─── Gateway (in-process, no network hop) ───────────────────────────────────────


def load_gateway():
    """Import deploy/gateway/server.py in-process and return its FastMCP gateway.

    Loaded by path rather than by import because deploy/ is not a package. This
    is the same trick the gateway itself uses to load each skill's server.py.
    """
    spec = importlib.util.spec_from_file_location("mia_agent_gateway", GATEWAY_SERVER)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load the MIA gateway from {GATEWAY_SERVER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.gateway


# ─── Models ─────────────────────────────────────────────────────────────────────


@dataclass
class ToolCall:
    """One tool invocation made while answering a turn."""

    name: str
    arguments: dict[str, Any]
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class AgentReply:
    """The channel-agnostic result of one turn. Every adapter renders this."""

    reply: str
    tools_called: list[str] = field(default_factory=list)
    requires_human: list[str] = field(default_factory=list)
    calls: list[ToolCall] = field(default_factory=list)
    stopped_early: bool = False


@dataclass
class Session:
    """Per-session conversation state. In-memory and deliberately not persisted."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    turns: int = 0


# ─── Helpers ────────────────────────────────────────────────────────────────────


def to_anthropic_tools(mcp_tools) -> list[dict[str, Any]]:
    """Convert MCP tool definitions into Anthropic tool schemas.

    MCP already speaks JSON Schema, so this is a field rename rather than a
    translation: name -> name, description -> description, inputSchema ->
    input_schema.
    """
    tools = []
    for tool in mcp_tools:
        tools.append(
            {
                "name": tool.name,
                "description": (tool.description or "").strip(),
                "input_schema": tool.inputSchema,
            }
        )
    return tools


def human_items(result: dict[str, Any]) -> list[str]:
    """Pull the honesty-contract items out of a tool result.

    Returns the human steps a tool flagged plus any warnings, so an adapter can
    render them structurally even if the model's prose were to drop them.
    """
    items: list[str] = []
    if result.get("requires_human"):
        steps = result.get("human_steps") or []
        items.extend(str(step) for step in steps)
        if not steps:
            items.append("This result needs a human step - see the notes.")
    items.extend(str(w) for w in (result.get("warnings") or []))
    return items


def _result_payload(result) -> dict[str, Any]:
    """Normalise a fastmcp CallToolResult into a plain dict for the model."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    texts = [getattr(block, "text", "") for block in getattr(result, "content", [])]
    joined = "\n".join(t for t in texts if t)
    try:
        parsed = json.loads(joined)
    except (ValueError, TypeError):
        return {"result": joined}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


def _text_of(response) -> str:
    """Concatenate the text blocks of a model response."""
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(p for p in parts if p).strip()


# ─── The agent ──────────────────────────────────────────────────────────────────


class MiaAgent:
    """An LLM wired to the live MIA skills. Transport-agnostic by construction."""

    def __init__(
        self,
        client: AsyncAnthropic | None = None,
        gateway=None,
        model: str = MODEL,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
        max_tool_iterations: int = MAX_TOOL_ITERATIONS,
        max_turns: int = MAX_TURNS,
        effort: str = EFFORT,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._client = client
        self._gateway = gateway if gateway is not None else load_gateway()
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.max_tool_iterations = max_tool_iterations
        self.max_turns = max_turns
        self.effort = effort
        self.system_prompt = system_prompt
        self.sessions: dict[str, Session] = {}
        self._tools: list[dict[str, Any]] | None = None

    # -- wiring ------------------------------------------------------------

    @property
    def client(self) -> AsyncAnthropic:
        """The Anthropic client, built on first use so importing needs no key."""
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise MissingAPIKeyError(
                    "ANTHROPIC_API_KEY is not set. Export it in your shell or put it "
                    "in deploy/agent/.env (gitignored). The agent never writes it to disk."
                )
            self._client = AsyncAnthropic(api_key=api_key)
        return self._client

    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover the gateway's tools and cache them as Anthropic schemas."""
        if self._tools is None:
            async with Client(self._gateway) as mcp:
                self._tools = to_anthropic_tools(await mcp.list_tools())
            logger.info("discovered %d tools from the gateway", len(self._tools))
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        """Run one gateway tool in-process, never raising on tool failure."""
        try:
            async with Client(self._gateway) as mcp:
                raw = await mcp.call_tool(name, arguments)
        except Exception as exc:  # surfaced to the model as an error tool_result
            logger.warning("tool %s failed: %s", name, exc)
            return ToolCall(name=name, arguments=arguments, ok=False, error=str(exc))
        return ToolCall(name=name, arguments=arguments, ok=True, result=_result_payload(raw))

    # -- the turn ----------------------------------------------------------

    async def chat(self, session_id: str, message: str) -> AgentReply:
        """Answer one user message, running the tool loop until the model is done."""
        session = self.sessions.setdefault(session_id, Session())
        if session.turns >= self.max_turns:
            raise TurnLimitError(
                f"This conversation hit its {self.max_turns}-turn limit. Start a new one to carry on."
            )
        session.turns += 1

        tools = await self.list_tools()
        messages = session.messages + [{"role": "user", "content": message}]

        calls: list[ToolCall] = []
        reply_text = ""
        stopped_early = False

        for _ in range(self.max_tool_iterations):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=self.system_prompt,
                tools=tools,
                messages=messages,
                output_config={"effort": self.effort},
            )

            # Claude may decline a request outright; check before reading content.
            if getattr(response, "stop_reason", None) == "refusal":
                reply_text = (
                    "I can't help with that request. I can run South African business "
                    "tax, payroll and compliance calculations - ask me one of those."
                )
                messages = messages[:-1]  # don't poison the history with a refused turn
                break

            messages = messages + [{"role": "assistant", "content": response.content}]
            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]

            if not tool_uses:
                reply_text = _text_of(response)
                break

            results = []
            for block in tool_uses:
                call = await self.call_tool(block.name, dict(block.input or {}))
                calls.append(call)
                payload = call.result if call.ok else {"error": call.error}
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(payload, default=str),
                        "is_error": not call.ok,
                    }
                )
            messages = messages + [{"role": "user", "content": results}]
        else:
            # Loop cap hit with the model still asking for tools. Say so rather
            # than silently returning a half-finished answer.
            stopped_early = True
            reply_text = (
                "I ran out of steps working through that one. Try asking for a single "
                "calculation at a time and I'll get you a clean answer."
            )

        session.messages = messages

        requires_human: list[str] = []
        for call in calls:
            if call.ok and call.result:
                for item in human_items(call.result):
                    if item not in requires_human:
                        requires_human.append(item)

        return AgentReply(
            reply=reply_text,
            tools_called=[c.name for c in calls],
            requires_human=requires_human,
            calls=calls,
            stopped_early=stopped_early,
        )

    def reset(self, session_id: str) -> None:
        """Drop a session's history."""
        self.sessions.pop(session_id, None)
