# file-annual-return-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Determine when a company's CIPC annual return is due, calculate the filing fee from turnover bands, and prepare/submit the return - the filing every SA company must make yearly or face deregistration.

**Regulator / authority:** Companies and Intellectual Property Commission (CIPC)

## Planned tools

- `check_due_date` — Determine the annual-return window from the company's registration anniversary.
- `calculate_filing_fee` — Calculate the annual return fee from the company's turnover band.
- `file_annual_return` — Submit the annual return via the CIPC portal.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

The CIPC annual-return fee table (turnover bands and amounts) and late-filing penalties require research against the live CIPC schedule.

Primary sources to verify against:

- CIPC annual returns portal (https://annualreturns.cipc.co.za)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/file-annual-return-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
