# lookup-afcfta-tariff-preference

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Given an HS code, origin and destination state party, return the AfCFTA preferential rate vs MFN, the applicable rules of origin, and the certificate-of-origin requirements - turning the continent's flagship trade deal into a callable tool.

**Regulator / authority:** African Continental Free Trade Area (AfCFTA) Secretariat

## Planned tools

- `lookup_tariff_preference` — Look up the AfCFTA preferential rate vs MFN for an HS code and trade lane.
- `check_rules_of_origin` — Return the applicable rules of origin for the product line.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Tariff phase-down schedules differ per state party and product; several rules-of-origin chapters remain under negotiation - all of it requires research against the AfCFTA e-Tariff Book rather than assumption.

Primary sources to verify against:

- AfCFTA e-Tariff Book (https://au-afcfta.org)
- national customs schedules

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/lookup-afcfta-tariff-preference
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
