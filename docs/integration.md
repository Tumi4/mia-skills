# Integrating mia-skills

Four ways to call the library, from zero-setup to fully custom. Every path exposes the same honest contract: verified constants (source URL + date in each skill), structured outputs, explicit `requires_human` steps, and a `get_status` tool per skill reporting its rule basis and last rule check.

---

## 1. Hosted gateway — one URL, zero setup

The fastest path, especially for non-developers: the gateway at `deploy/gateway` composes **every live skill** into a single remote MCP endpoint.

- **claude.ai / Claude Desktop:** Settings → Connectors → *Add custom connector* → paste the gateway URL (`https://<service>.onrender.com/mcp`).
- **Cursor / other MCP clients:** add the same URL as a remote MCP server (streamable HTTP).

Tools are namespaced per skill: `turnover_calculate_turnover_tax`, `vat_check_registration_required`, `paye_calculate_monthly_paye`, `sdl_calculate_sdl`, `carbon_calculate_carbon_tax`, `provtax_calculate_provisional_payment`, `s12b_calculate_deduction`, plus `<namespace>_get_status` everywhere and `gateway_status` for the full inventory.

Deployment walkthrough: [`deploy/gateway/README.md`](../deploy/gateway/README.md).

---

## 2. Claude Desktop — run skills locally

Each skill is a standalone MCP server. Install what you need and register it in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "section-12b": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-section-12b-solar-deduction/server.py"]
    },
    "turnover-tax": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-turnover-tax-south-africa/server.py"]
    },
    "vat-registration": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/check-vat-registration-south-africa/server.py"]
    },
    "paye": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-paye-south-africa/server.py"]
    },
    "sdl": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-sdl-south-africa/server.py"]
    },
    "carbon-tax": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-carbon-tax-south-africa/server.py"]
    },
    "provisional-tax": {
      "command": "python",
      "args": ["C:/path/to/mia-skills/skills/calculate-provisional-tax-south-africa/server.py"]
    }
  }
}
```

Prerequisite per skill: `pip install -e ".[dev]"` inside the skill folder (or just `pip install fastmcp pydantic` once, globally).

---

## 3. Cursor and other MCP-native editors

`~/.cursor/mcp.json` takes the same shape — `command` + `args` per skill, or the hosted URL as a remote server. One skill = one entry; add only what you use.

---

## 4. Custom agents (Python)

```python
from fastmcp import Client
import asyncio

async def main():
    # local: Client("path/to/skills/<skill>/server.py") also works
    async with Client("https://<service>.onrender.com/mcp") as c:
        result = await c.call_tool(
            "paye_calculate_monthly_paye",
            {"input": {"monthly_salary_zar": 30_000, "age": 40, "medical_scheme_members": 3}},
        )
        print(result.data)

asyncio.run(main())
```

---

## The honesty contract (applies on every path)

1. **`get_status` first.** Every skill reports `status` (alpha/scaffold), `rule_basis`, and `last_rule_check`. Agents should surface this to users.
2. **`requires_human` is not decoration.** When an output flags human steps (practitioner confirmation, real filings, sworn affidavits), the calling agent must pass them on, not swallow them.
3. **Scaffolds say so.** Scaffold skills return structured not-implemented responses; the hosted gateway refuses to mount them at all.
4. **Constants are dated.** Each skill's `server.py` cites the primary source URL and the date checked. If `last_rule_check` looks old, re-verify before relying on the numbers.
