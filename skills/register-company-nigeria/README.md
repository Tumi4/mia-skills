# register-company-nigeria

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Wrap the Nigerian company registration flow on the CAC portal: name reservation, incorporation, TIN issuance - alongside Kenya, the start of the library's pan-African coverage.

**Regulator / authority:** Corporate Affairs Commission (CAC)

## Planned tools

- `check_name_availability` — Search proposed company names against the CAC registry.
- `prepare_registration` — Prepare the CAC incorporation filing pack.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

Current CAC fees, stamp-duty treatment, form names and timelines require research against live CAC sources - Nigerian figures are deliberately absent rather than guessed.

Primary sources to verify against:

- https://www.cac.gov.ng
- CAC company registration portal

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/register-company-nigeria
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
