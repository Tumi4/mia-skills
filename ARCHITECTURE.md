# Architecture

This document describes the technical architecture of `mia-skills` and how it fits into the broader MIA stack.

---

## The bigger picture: MIA's six-layer stack

MIA is the operating system for African entrepreneurship. It has six layers, bottom-up:

```
┌────────────────────────────────────────────────────────────────┐
│  6 · Agent layer        (orchestration, voice, chat, browser)  │
├────────────────────────────────────────────────────────────────┤
│  5 · Identity & context (persistent founder profile)           │
├────────────────────────────────────────────────────────────────┤
│  4 · Knowledge layer    (benchmarks, comparables, intel)       │
├────────────────────────────────────────────────────────────────┤
│  3 · Relationship graph (funders, mentors, peers, services)    │
├────────────────────────────────────────────────────────────────┤
│  2 · ACTION LIBRARY     ← this repo                            │
├────────────────────────────────────────────────────────────────┤
│  1 · Data infrastructure (outcomes, flows, regulatory shifts)  │
└────────────────────────────────────────────────────────────────┘
```

`mia-skills` is **layer 2** — the Africa-first action library. It is the most defensible part of the stack because it is built by coordinating with hundreds of regulators, banks, and government registries across 54 countries. Capital cannot buy this overnight. Years of focused work can.

The other layers live elsewhere:

- **Layer 1 (Data infrastructure)** — lives in `mia-core` (private). Outcomes graph, capital flow data, network graph. The trillion-dollar revenue line.
- **Layer 3 (Relationship graph)** — lives in `mia-core` and the existing MIA portal.
- **Layer 4 (Knowledge)** — lives in `mia-core`.
- **Layer 5 (Identity & context)** — `mia-identity` (planned, separate repo).
- **Layer 6 (Agent layer)** — `mia-agents` (planned, separate repo).

This separation is deliberate. Each layer can be rebuilt or replaced without touching the others. Skills work standalone today; tomorrow they get orchestrated by MIA's agents.

---

## What's in this repo

```
mia-skills/
├── skills/                         # one directory per skill (MCP server)
│   └── register-company-south-africa/
├── docs/                           # integration guides
├── scripts/                        # tooling (skill scaffolding, validation)
├── .github/workflows/              # CI
├── ARCHITECTURE.md                 # this file
├── CLAUDE.md                       # AI agent orientation
├── CONTRIBUTING.md                 # how to add a skill
└── README.md                       # public-facing overview
```

---

## The MCP contract

Every skill in this repo is an MCP (Model Context Protocol) server. MCP is the open standard pioneered by Anthropic in late 2024 for AI tools to communicate with external systems in a composable way.

A skill exposes:

- **Tools** — callable functions with typed inputs and outputs (most common)
- **Resources** — readable data sources (used for static reference data like jurisdiction tables)
- **Prompts** — reusable prompt templates (used for skills that involve LLM reasoning)

Any MCP client — Claude Desktop, Cursor, ChatGPT (via plugins/connectors), custom agents — can connect to a skill and call its tools.

This is what enables the "plug-in, plug-out" vision: founders can use MIA's skills from whatever AI tool they prefer, and MIA's hosted product can call any external MCP-compatible tool.

---

## Skill schema

Every skill has a `skill.json` file describing its metadata. The schema:

```json
{
  "name": "register-company-south-africa",
  "version": "0.1.0",
  "description": "Register a Pty Ltd company in South Africa via CIPC",
  "jurisdiction": ["ZA"],
  "category": "company-formation",
  "regulators": ["CIPC"],
  "maintainer": {
    "name": "Aquarius Foundation",
    "email": "skills@theaquariusfoundation.org",
    "github": "aquariusfoundation"
  },
  "status": "scaffold",
  "requires_credentials": ["CIPC_USERNAME", "CIPC_PASSWORD"],
  "requires_human_steps": [
    "Director identity verification (in-person or via accredited verifier)",
    "BEE affidavit signature"
  ],
  "estimated_completion_time": "14 business days",
  "estimated_cost_zar": 225,
  "license": "Apache-2.0"
}
```

Status values:
- `scaffold` — directory structure and stub tools exist; not production-ready
- `alpha` — working end-to-end for happy path; rough edges
- `beta` — production-ready for primary path; edge cases may need human fallback
- `stable` — battle-tested; semantic versioning enforced
- `deprecated` — being phased out; alternatives listed in README

---

## Standard input/output patterns

Every tool input includes:
- The minimum data needed for the operation
- Optional fields for context (e.g. founder's other companies)

Every tool output includes:
- The primary result of the operation
- A `requires_human` field (bool + list of steps if true)
- A `next_actions` field suggesting follow-up tools to call
- A `cost_estimate` field where applicable
- A `timeline_estimate` field where applicable

Example output schema:

```python
class StandardOutput(BaseModel):
    success: bool
    result: dict | None = None
    requires_human: bool = False
    human_steps: list[str] = []
    next_actions: list[str] = []
    cost_estimate_zar: float | None = None
    timeline_estimate_days: int | None = None
    notes: str = ""
```

---

## Browser automation strategy

Many African regulators have no public API. Some examples:
- CIPC has limited API access; e-services is browser-only
- SARS eFiling is browser-only with hCaptcha
- Most provincial tender portals are browser-only
- Most African central bank exchange control filings are browser-only

For these, we use **Playwright** with the following rules:

1. **Headless by default** — but skill must support `headless=False` for debugging
2. **Explicit waits** — no `time.sleep()`; use Playwright's wait conditions
3. **No credential storage** — credentials come from env vars per session
4. **Captcha policy** — if a captcha blocks automation, return `requires_human=True` with clear instructions, don't try to solve it
5. **Audit trail** — every browser action is logged to a structured log (not stdout)
6. **Idempotent where possible** — running a skill twice should not create duplicate registrations

When an API does exist, prefer it. Document the fallback to browser automation explicitly.

---

## Versioning and stability

Each skill follows semantic versioning:

- **Major** — breaking changes to tool signatures or behavior
- **Minor** — new tools added, non-breaking
- **Patch** — bug fixes, internal refactors

Once a skill reaches `stable` status, breaking changes require:
1. A deprecation notice in the prior minor version
2. At least 90 days of overlap where both versions are runnable
3. A migration guide in the skill's README

---

## How `mia-core` consumes this repo

The proprietary MIA core platform consumes skills from this repo in two ways:

1. **Static installation** — selected skills are vendored into mia-core at build time, used by MIA's hosted agents
2. **Dynamic discovery** — mia-core can call skills from this repo as remote MCP servers, useful for community-maintained skills not yet vendored

Premium skills (advanced filings, multi-jurisdiction orchestration, automated DD packets) live in `mia-core` and are not open-source. The line is drawn at: anything that requires the proprietary outcomes graph, premium funder data, or paid integrations.

---

## Future architectural decisions (parked)

These are deliberately not solved yet:

- **Cross-skill orchestration** — should be in `mia-agents`, not here
- **Persistent state across sessions** — should be in `mia-identity`, not here
- **Multi-tenant credential management** — should be in `mia-core`, not here
- **Telemetry and analytics** — needs careful design; opt-in only, no founder data leaks
- **Skill marketplace economics** — if community maintainers want compensation, design later; for now, all skills are free contributions

When in doubt, the answer is: this repo does one thing, well. Action skills. Everything else lives somewhere else.

---

*Maintained by the MIA technical team. Last updated: May 2026.*
