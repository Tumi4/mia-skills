# register-company-south-africa

Register a private company (Pty Ltd) in South Africa via the Companies and Intellectual Property Commission (CIPC).

**Status:** Scaffold (v0.1.0). Tool signatures stable; underlying integrations are stubs.

---

## What it does

Wraps the seven-step CIPC company registration process into composable MCP tools any AI agent can call:

1. **Check name availability** — Is the proposed company name free with CIPC?
2. **Reserve name** — Lock the name for 6 months while you prepare filing
3. **Estimate costs** — How much will registration plus ancillary services cost?
4. **Prepare filing** — Generate the MOI (CoR15.1A), Notice of Incorporation (CoR14.1), and director consents
5. **Submit registration** — File with CIPC (requires explicit consent — irreversible)
6. **Check status** — Track an in-flight registration
7. **Get status** — Find out which tools are working vs stubbed

---

## What it requires

- **A CIPC e-services account.** Set up at https://eservices.cipc.co.za. Free.
- **Environment variables:**
  ```bash
  export CIPC_USERNAME=your-cipc-username
  export CIPC_PASSWORD=your-cipc-password
  ```
- **For each director:** Full name, RSA ID (or passport for foreign nationals), residential address, email, phone

---

## How to use it

### As a standalone MCP server (any client)

```bash
cd skills/register-company-south-africa
pip install -e .
python server.py
```

### From Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "register-company-sa": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/register-company-south-africa/server.py"],
      "env": {
        "CIPC_USERNAME": "your-username",
        "CIPC_PASSWORD": "your-password"
      }
    }
  }
}
```

Then in Claude: *"Use the register-company-sa tools to check if 'Sunbright Holdings (Pty) Ltd' is available."*

### From a custom Python agent

```python
from mcp.client import Client

async with Client.connect_stdio(
    command="python",
    args=["server.py"],
) as client:
    tools = await client.list_tools()
    result = await client.call_tool(
        "check_name_availability",
        {"name": "Sunbright Holdings"}
    )
    print(result)
```

---

## Limits and human-required steps

This skill **cannot** complete a registration end-to-end without human involvement. Always at least these steps require a person:

1. **Director ID verification.** Must be done in person at SAPS or via an accredited verifier (Lexis Refinitiv, Compliance Online). The skill cannot bypass this.
2. **MOI signature.** All directors must sign the Memorandum of Incorporation before a Commissioner of Oaths.
3. **B-BBEE EME affidavit.** Must be sworn before a Commissioner of Oaths.

The skill surfaces these via the `requires_human` field in every output. **Founders should never assume a skill output means a step is done.** Always verify with CIPC directly before any irreversible action.

Other limits:
- The skill targets only Pty Ltd (private companies). Public companies (Ltd), state-owned (SOC), non-profit (NPC), and personal liability (Inc.) are out of scope.
- Foreign-only directorships add complexity around tax residency that this skill does not handle.
- Trust-owned shareholding requires additional steps not yet automated.

---

## Cost and timeline (honest estimates)

| Item | Cost (ZAR) | Days |
|---|---|---|
| Name reservation | 50 | 1 |
| CIPC registration | 175 | 7–10 |
| B-BBEE EME affidavit | 0 (DIY) or ~500 (via service) | 1 |
| Tax registration (automatic) | 0 | included |
| **Total minimum** | **225** | **10–14 business days** |

Optional (not handled by this skill):
- Registered office address service: R200–R500/month
- Company secretary service: R3,000–R8,000/year
- Initial accounting setup: R2,000–R5,000

---

## Compared to alternatives

| Option | Cost | Time | Quality |
|---|---|---|---|
| **DIY via CIPC e-services** | R225 | 10–14 days | Requires you to learn the system |
| **Standard service (SwiftReg, etc.)** | R690–R1,500 | 5–7 days | Convenient; opaque |
| **Premium service (lawyer)** | R5,000–R15,000 | 5–10 days | Hand-holding; expensive |
| **mia-skills (this skill, eventually)** | R225 + your time | 10–14 days | Composable with your agent stack; transparent |

---

## Roadmap

See `get_status` tool for the live list. Next milestones:

1. Wire up CIPC e-services login via Playwright
2. Real `check_name_availability` implementation
3. MOI (CoR15.1A) PDF generation from Pydantic input
4. `reserve_name` flow with explicit confirmation
5. Full document bundle generation
6. Optional: SwiftReg API integration as fallback

---

## Liability

This skill is provided as-is, under Apache 2.0. It is a tool, not legal advice. Always verify outputs with CIPC directly before any irreversible action. The maintainers are not responsible for misfilings, missed deadlines, or rejected applications.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org

Issues and PRs: https://github.com/aquariusfoundation/mia-skills
