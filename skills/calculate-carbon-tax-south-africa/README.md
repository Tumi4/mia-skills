# calculate-carbon-tax-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Determine whether an entity's activities trigger carbon tax, and calculate the liability from emissions data using the current rate per tonne CO2e and the applicable allowances (basic, trade-exposure, performance) - directly aligned with MIA's climate focus.

**Regulator / authority:** South African Revenue Service (SARS)

## Planned tools

- `check_liability` — Determine whether activities fall within carbon tax scope.
- `calculate_carbon_tax` — Calculate carbon tax from tonnes CO2e and applicable allowances.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

The current carbon tax rate per tonne CO2e (it escalates annually), phase rules and allowance percentages require research against live SARS pages before any constant is coded.

Primary sources to verify against:

- SARS carbon tax pages (https://www.sars.gov.za/customs-and-excise/excise/environmental-levy-products/carbon-tax/)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/calculate-carbon-tax-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
