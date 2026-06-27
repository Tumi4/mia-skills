# mia-skills

**Africa-first action skills for AI agents.** Open-source MCP servers that let any AI tool — Claude, ChatGPT, Cursor, your own agent — actually *do* things in African operational reality. Register companies. Open bank accounts. File grants. Navigate regulators. Integrate payment rails.

Part of [MIA — Made in Africa](https://mia-capital-advisor.onrender.com), the operating system for African entrepreneurship.

---

## Why this exists

There are dozens of agentic AI tools today. None of them know how to register a Pty Ltd in South Africa, open a USD account in Lagos, file an AfDB grant, navigate SARB exchange controls, or claim Section 12J credits. African founders coordinate this knowledge in WhatsApp groups, Notion pages, and tribal memory.

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

```bash
# Clone
git clone https://github.com/aquariusfoundation/mia-skills
cd mia-skills

# Install a skill
cd skills/register-company-south-africa
pip install -e .

# Run as MCP server
python server.py

# Or connect from Claude Desktop, Cursor, etc. via mcp.json config
```

See [`docs/integration.md`](docs/integration.md) for connecting to Claude Desktop, Cursor, ChatGPT, and custom agents.

## Available skills (v0.1)

| Skill | Jurisdiction | Status | Maintainer |
|---|---|---|---|
| `calculate-section-12b-solar-deduction` | 🇿🇦 South Africa (SARS) | **Working (alpha)** | @aquariusfoundation |
| `register-company-south-africa` | 🇿🇦 South Africa (CIPC) | Scaffold | @aquariusfoundation |
| `open-usd-account-mercury` | 🇺🇸 via 🇿🇦 | Planned | — |
| `file-afdb-grant` | Pan-African (AfDB) | Planned | — |
| `navigate-sarb-exchange-control` | 🇿🇦 South Africa | Planned | — |
| `claim-section-12j` | 🇿🇦 South Africa | Planned | — |
| `integrate-mpesa` | 🇰🇪 Kenya | Planned | — |
| `register-company-nigeria` | 🇳🇬 Nigeria (CAC) | Planned | — |
| `register-company-kenya` | 🇰🇪 Kenya (BRS) | Planned | — |
| `register-company-rwanda` | 🇷🇼 Rwanda (RDB) | Planned | — |
| `apply-afcfta-tariff-preference` | Pan-African (AfCFTA) | Planned | — |

Want to contribute a skill? See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Architecture

```
mia-skills/
├── skills/                        # one directory per skill
│   ├── register-company-south-africa/
│   │   ├── server.py              # FastMCP server entry point
│   │   ├── skill.json             # schema, metadata, version
│   │   ├── README.md              # user-facing docs
│   │   └── tests/                 # required: pytest
│   └── ...
├── docs/                          # integration guides, architecture
├── .github/workflows/             # CI: tests, schema validation
├── ARCHITECTURE.md                # technical architecture
├── CONTRIBUTING.md                # how to add a skill
├── CLAUDE.md                      # orientation for Claude Code
└── README.md                      # this file
```

## License

Apache 2.0. Use freely. Contribute back what you learn.

## Maintained by

[The Aquarius Foundation](https://theaquariusfoundation.org) and the MIA community.

For commercial integrations, premium skills, and the proprietary engine, see [MIA](https://mia-capital-advisor.onrender.com).
