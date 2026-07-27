# reserve-company-name-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Check availability of a proposed company name and reserve it with CIPC ahead of incorporation. Designed to be called standalone or internally by register-company-south-africa (composable-skills principle).

**Regulator / authority:** Companies and Intellectual Property Commission (CIPC)

## Planned tools

- `check_name_availability` — Check whether a proposed company name is available with CIPC.
- `reserve_name` — Reserve an available company name with CIPC (form COR9.1).
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Current CIPC name-reservation fee and reservation validity period require research on the live CIPC fee schedule - do not assume the commonly quoted figures.

Primary sources to verify against:

- CIPC e-services (https://eservices.cipc.co.za)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/reserve-company-name-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
