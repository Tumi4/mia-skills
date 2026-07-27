# check-grant-eligibility-seda-sefa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Map a business's profile (stage, sector, turnover, ownership) against live SEDA programmes and SEFA funding instruments, returning which are worth applying to and what each requires.

**Regulator / authority:** Small Enterprise Development Agency (SEDA) and Small Enterprise Finance Agency (SEFA)

## Planned tools

- `list_programmes` — List current SEDA programmes and SEFA instruments with their criteria.
- `check_eligibility` — Match a business profile against programme criteria.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

The live SEDA programme list and SEFA instrument criteria require research - both change often enough that a static snapshot without a last-verified date would be dishonest.

Primary sources to verify against:

- https://www.seda.org.za
- https://www.sefa.org.za

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/check-grant-eligibility-seda-sefa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
