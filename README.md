# mia-skills

[![CI](https://github.com/Tumi4/mia-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Tumi4/mia-skills/actions/workflows/ci.yml)

**Africa-first action skills for AI agents.** Open-source MCP servers that let any AI tool — Claude, ChatGPT, Cursor, your own agent — actually *do* things in African operational reality. Register companies. Open bank accounts. File grants. Navigate regulators. Integrate payment rails.

Part of [MIA — Made in Africa](https://mia-capital-advisor.onrender.com), the operating system for African entrepreneurship.

---

## Why this exists

There are dozens of agentic AI tools today. None of them know how to register a Pty Ltd in South Africa, open a USD account in Lagos, file an AfDB grant, navigate SARB exchange controls, or claim a Section 12B solar deduction. African founders coordinate this knowledge in WhatsApp groups, Notion pages, and tribal memory.

This repo turns that tribal knowledge into composable, AI-callable skills. Anyone can contribute. Every successful execution improves the next one.

## What's a "skill" here

A skill is a self-contained MCP (Model Context Protocol) server that exposes one or more tools for a specific African operational task. Skills are:

- **Composable** — call them from any MCP-compatible AI client
- **Open-source** — Apache 2.0 licensed, community-contributed
- **Jurisdiction-specific** — one skill per country/regulator/process
- **Versioned** — semantic versioning, breaking changes documented
- **Tested** — every skill ships with tests; CI enforces this
- **Honest about limits** — if a step requires a human, the skill says so

## Quick start

**Zero-setup (hosted):** add the gateway URL as a custom connector in Claude — one URL serves every live skill. See [`deploy/gateway/README.md`](deploy/gateway/README.md).

**Run a skill yourself:**

```bash
# Clone
git clone https://github.com/aquariusfoundation/mia-skills
cd mia-skills

# Install a skill
cd skills/calculate-turnover-tax-south-africa
pip install -e .

# Run as MCP server
python server.py

# Or connect from Claude Desktop, Cursor, etc. via mcp.json config
```

See [`docs/integration.md`](docs/integration.md) for Claude Desktop, Cursor, the hosted gateway, and custom agents.

## Available skills

**Working (alpha)** = every tool implemented, every constant verified against the live primary source (date in each skill's `last_rule_check`). **Scaffold** = honest stubs: stable tool signatures that return structured not-implemented responses, no invented regulatory figures. Last updated: 30 July 2026.

| Skill | Jurisdiction | Status | Tests | Maintainer |
|---|---|---|---|---|
| `calculate-section-12b-solar-deduction` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 21 | @aquariusfoundation |
| `calculate-turnover-tax-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 31 | @aquariusfoundation |
| `check-vat-registration-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 19 | @aquariusfoundation |
| `calculate-paye-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 21 | @aquariusfoundation |
| `calculate-sdl-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 15 | @aquariusfoundation |
| `calculate-carbon-tax-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 15 | @aquariusfoundation |
| `calculate-provisional-tax-south-africa` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | 24 | @aquariusfoundation |
| `register-company-south-africa` | 🇿🇦 South Africa (CIPC) | Scaffold | 13 | @aquariusfoundation |
| `reserve-company-name-south-africa` | 🇿🇦 South Africa (CIPC) | Scaffold | 4 | @aquariusfoundation |
| `file-annual-return-south-africa` | 🇿🇦 South Africa (CIPC) | Scaffold | 4 | @aquariusfoundation |
| `register-uif-south-africa` | 🇿🇦 South Africa (Employment & Labour) | Scaffold | 4 | @aquariusfoundation |
| `apply-tax-clearance-south-africa` | 🇿🇦 South Africa (SARS) | Scaffold | 4 | @aquariusfoundation |
| `generate-bbbee-affidavit-south-africa` | 🇿🇦 South Africa (the dtic) | Scaffold | 4 | @aquariusfoundation |
| `check-grant-eligibility-seda-sefa` | 🇿🇦 South Africa (SEDA/SEFA) | Scaffold | 4 | @aquariusfoundation |
| `register-company-kenya` | 🇰🇪 Kenya (BRS) | Scaffold | 4 | @aquariusfoundation |
| `register-company-nigeria` | 🇳🇬 Nigeria (CAC) | Scaffold | 4 | @aquariusfoundation |
| `lookup-afcfta-tariff-preference` | Pan-African (AfCFTA) | Scaffold | 4 | @aquariusfoundation |
| `open-usd-account-mercury` | 🇺🇸 via 🇿🇦 | Planned | — | — |
| `file-afdb-grant` | Pan-African (AfDB) | Planned | — | — |
| `navigate-sarb-exchange-control` | 🇿🇦 South Africa | Planned | — | — |
| `integrate-mpesa` | 🇰🇪 Kenya | Planned | — | — |
| `register-company-rwanda` | 🇷🇼 Rwanda (RDB) | Planned | — | — |

**200 tests passing** across the library (195 skill tests + 5 gateway contract tests), plus 73 more covering the agent and web surfaces — 273 in the repo. The hosted [gateway](deploy/gateway/README.md) serves the seven live skills — 27 tools — from one MCP URL; scaffolds are never mounted on the hosted surface.

Want to contribute a skill? See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Architecture

```
mia-skills/
├── skills/                        # one directory per skill (standalone MCP server)
│   ├── calculate-turnover-tax-south-africa/
│   │   ├── server.py              # FastMCP server entry point
│   │   ├── skill.json             # schema, metadata, version
│   │   ├── README.md              # user-facing docs
│   │   └── tests/                 # required: pytest
│   └── ...
├── deploy/gateway/                # hosted MCP endpoint composing the LIVE skills
├── deploy/agent/                  # the web surfaces: landing page, chat, POST /chat
│   └── static/index.html          # the landing page (constants generated, see below)
├── scripts/gen_web_constants.py   # regenerates the page's JS constants from the Python
├── docs/                          # integration guides, architecture
├── .github/workflows/             # CI: pytest, the constants guard, ruff
├── render.yaml                    # Render deployment: gateway + agent
├── ruff.toml                      # lint config for everything outside skills/
├── ARCHITECTURE.md                # technical architecture
├── CONTRIBUTING.md                # how to add a skill
├── CLAUDE.md                      # orientation for Claude Code
└── README.md                      # this file
```

### One source of truth for every number

The landing page renders a live turnover-tax and VAT comparison in the browser,
before any network call, so it works on a bad connection and with JavaScript off.
That needs the thresholds in JavaScript as well as Python — and two copies of a tax
threshold is exactly the failure this project exists to argue against.

So the JavaScript copy is **generated**, fenced between sentinels, and CI asserts it
still matches:

```bash
python scripts/gen_web_constants.py           # regenerate after changing a skill
python scripts/gen_web_constants.py --check   # what CI runs; fails on drift
```

When the page is served by `deploy/agent` it additionally calls `GET /api/position`,
which computes both columns through the real skills. The generated constants are the
offline fallback; the live answer wins when it arrives. Neither path can drift from
the Python without the build going red.

## License

Apache 2.0. Use freely. Contribute back what you learn.

## Maintained by

[The Aquarius Foundation](https://theaquariusfoundation.org) and the MIA community.

For commercial integrations, premium skills, and the proprietary engine, see [MIA](https://mia-capital-advisor.onrender.com).
