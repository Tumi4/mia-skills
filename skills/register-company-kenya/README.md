# register-company-kenya

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Wrap the Kenyan company registration flow: name search and reservation, incorporation forms, KRA PIN linkage - the first non-South-African jurisdiction in the library.

**Regulator / authority:** Business Registration Service (BRS) via eCitizen

## Planned tools

- `check_name_availability` — Search proposed company names against the BRS registry.
- `prepare_registration` — Prepare the incorporation filing pack for eCitizen submission.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Current BRS fees, form names and processing timelines require research against live BRS/eCitizen sources - Kenyan figures are deliberately absent rather than guessed.

Primary sources to verify against:

- https://brs.go.ke
- eCitizen (https://www.ecitizen.go.ke)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/register-company-kenya
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
