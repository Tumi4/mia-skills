# apply-tax-clearance-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Request and share a Tax Compliance Status (TCS) PIN - required for tenders, some contracts and foreign investment allowances. Checks readiness (returns filed, no debt) before applying via eFiling.

**Regulator / authority:** South African Revenue Service (SARS)

## Planned tools

- `check_compliance_readiness` — Pre-check the common blockers to a compliant TCS (outstanding returns, debt).
- `request_tcs_pin` — Request the Tax Compliance Status PIN via eFiling.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Current TCS request types and their criteria require research on the live SARS TCS pages.

Primary sources to verify against:

- SARS Tax Compliance Status pages (https://www.sars.gov.za)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/apply-tax-clearance-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
