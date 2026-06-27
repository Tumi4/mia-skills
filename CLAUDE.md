# CLAUDE.md

This file orients Claude Code (and any other AI assistant) to the mia-skills project. Read this first in every session.

---

## Project context

**What this is:** An open-source library of Africa-first action skills, exposed as MCP (Model Context Protocol) servers. Each skill wraps a specific African operational task (company registration, banking, grants, regulatory filings, payment integrations) and makes it callable by any AI agent.

**Why it exists:** African founders need fundamentally different action skills than the US/EU developer-market norm. None of the existing US-built founder tooling (Stripe Atlas, Doola, Mercury, Carta, etc.) serves African jurisdictions. This repo is the open-source moat that turns African tribal knowledge into composable AI-callable infrastructure.

**Who builds it:** Tumelo Ncube (technical founder) + the community. Maintained under The Aquarius Foundation and MIA Technologies.

**Where it fits:** This is the open-source surface of MIA's stack. There's a proprietary engine (`mia-core`, private) and a hosted product (the MIA portal at mia-capital-advisor.onrender.com). The skills here are usable standalone OR composed by MIA's agents.

---

## Architectural principles

1. **One skill = one MCP server.** No mega-servers. Each skill is independently versioned, tested, deployable.
2. **Open at the surface, proprietary at the engine.** This repo is fully open-source. The proprietary engine (mandates, outcomes graph, premium skills) lives elsewhere.
3. **Jurisdiction-explicit.** Every skill name includes the country/regulator. `register-company-south-africa`, not `register-company`.
4. **Honest about humans.** If a step needs a human signature, lawyer review, in-person KYC, or regulator approval, the skill says so explicitly via a structured `requires_human` response.
5. **No hidden state.** Skills are stateless by default. Anything stored is opt-in via a clearly documented persistence layer.
6. **Composable, not monolithic.** Skills should call each other where possible (e.g. `register-company-sa` can call `reserve-name-sa` internally) but stay independently runnable.
7. **Test what you ship.** Every PR with a new skill must include passing tests. CI enforces this.

---

## Tech stack

- **Language:** Python 3.11+ (skills); TypeScript reserved for future agent orchestration layer
- **MCP framework:** [FastMCP](https://github.com/jlowin/fastmcp) — the standard Python MCP server framework
- **Validation:** Pydantic v2 for all inputs/outputs
- **Web automation (where APIs don't exist):** Playwright (preferred) or Selenium
- **HTTP:** `httpx` (async) over `requests`
- **Testing:** `pytest` + `pytest-asyncio`
- **Linting:** `ruff` (formatting + linting in one)
- **Packaging:** `pyproject.toml` per skill; `uv` recommended for fast installs

---

## Code conventions

### File layout per skill

```
skills/<skill-name>/
├── server.py           # FastMCP server, tool definitions
├── skill.json          # schema, metadata, version, maintainer
├── README.md           # user-facing: what it does, how to use it, limitations
├── pyproject.toml      # dependencies, package metadata
├── src/<skill_name>/   # implementation modules (private)
│   ├── __init__.py
│   ├── client.py       # external API/web client
│   ├── models.py       # Pydantic models
│   └── validators.py   # input validation logic
└── tests/
    ├── test_server.py  # MCP tool tests
    └── test_client.py  # unit tests for client logic
```

### Naming

- Skill directories: `kebab-case` matching the MCP server name (e.g. `register-company-south-africa`)
- Python modules: `snake_case` (e.g. `register_company_south_africa`)
- Tool function names exposed via MCP: clear verb-first (`check_name_availability`, `prepare_filing`)
- Pydantic models: `PascalCase`

### Tool design

Every MCP tool function should:
1. Have explicit Pydantic input and output models
2. Return structured data, never raw strings
3. Document limits in the docstring (e.g. "Requires CIPC e-services account; KYC must be done in-person")
4. Include a `requires_human` field in the output if any step blocks on a human
5. Never silently fail — raise typed exceptions on hard errors

### Example

```python
from fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("my-skill")

class Input(BaseModel):
    company_name: str

class Output(BaseModel):
    available: bool
    alternatives: list[str] = []
    requires_human: bool = False
    notes: str = ""

@mcp.tool()
async def check_name(input: Input) -> Output:
    """Check if a company name is available. Hits CIPC name reservation API.

    Limits:
    - Requires valid CIPC enterprise account credentials in env
    - Rate-limited to 60 requests/hour by CIPC
    - Does not reserve the name; use `reserve_name` for that
    """
    # implementation...
```

---

## Common commands

```bash
# Set up a new skill from template (TODO: build this script)
./scripts/new-skill.sh <skill-name>

# Run a skill locally
cd skills/<skill-name> && python server.py

# Test a skill
cd skills/<skill-name> && pytest

# Test all skills
pytest skills/

# Lint everything
ruff check skills/
ruff format skills/

# Validate all skill.json files against schema
python scripts/validate_schemas.py
```

---

## Pitfalls to avoid

- **Don't build a mega-server.** Each skill stays standalone. Resist consolidating "for convenience."
- **Don't assume APIs exist.** Many African regulators have no public API. Browser automation via Playwright is a legitimate path.
- **Don't store credentials in the repo.** Use env vars. Document required env vars in each skill's README.
- **Don't promise more than the skill delivers.** If CIPC takes 14 business days, say 14 business days. Founders will not forgive false promises from automated tooling.
- **Don't skip the `requires_human` flag.** Most African operational processes have at least one human step (notarization, in-person KYC, signature). Be explicit.
- **Don't bypass tests.** No PR merges without tests. Even scaffolds need at least one passing structural test.
- **Don't reinvent agents here.** This repo is skills only. Orchestration belongs in `mia-core` or in the user's own agent layer.

---

## Tumelo's preferences

- Windows 10, VSCode, projects on D: drive
- Comfortable in Python and TypeScript; learning Rust slowly
- Uses Lovable for UI work, GitHub for code, Duda for client sites
- Has Ollama running `qwen2.5-coder:7b` locally and Continue.dev wired to OpenRouter
- Prefers explicit code over clever code
- Wants tests but doesn't need 100% coverage — pragmatic coverage on critical paths
- Likes good README files; will read CLAUDE.md every session

---

## Working with Claude Code on this repo

When in doubt:
1. Read this CLAUDE.md and ARCHITECTURE.md first
2. Check `skills/register-company-south-africa/` as the reference implementation
3. Follow the file layout exactly
4. Run `pytest` before suggesting a commit
5. Use small, atomic commits with clear messages
6. If you're about to add a dependency, ask first — keep the surface small

If a task is ambiguous, ask for clarification before writing code. Tumelo prefers a 30-second clarification question over a 30-minute refactor.

---

## Current priorities (rolling)

1. **Ship `register-company-south-africa` to working v0.1.** This is the demo skill for the next investor meeting.
2. **Write the skill template + `new-skill.sh` scaffolding script.**
3. **Set up CI** (GitHub Actions running pytest + ruff + schema validation).
4. **Document the integration story for Claude Desktop, Cursor, and a custom agent.**
5. **Land the second skill** (`open-usd-account-mercury` or `claim-section-12j`).

Move things off this list as they ship. Keep it short.

---

*Last updated: May 2026. Maintained by Tumelo Ncube and the MIA community.*
