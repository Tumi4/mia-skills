# register-uif-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Walk a new employer through UIF registration: determine the obligation, prepare the registration on u-Filing, and register employees - the sibling obligation to the SARS-collected contributions computed by calculate-paye-south-africa.

**Regulator / authority:** Department of Employment and Labour (u-Filing)

## Planned tools

- `check_registration_obligation` — Determine whether an employer must register for UIF.
- `prepare_registration` — Prepare the employer UIF registration for u-Filing.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Registration forms (e.g. UI-8/UI-19), employee-hours thresholds and domestic-employer rules require research against the Department of Employment and Labour's current pages.

Primary sources to verify against:

- u-Filing (https://ufiling.labour.gov.za)
- Department of Employment and Labour UIF pages

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/register-uif-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
