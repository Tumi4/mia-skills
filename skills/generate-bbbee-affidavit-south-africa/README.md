# generate-bbbee-affidavit-south-africa

⚠️ **SCAFFOLD — not yet implemented.** Tool signatures are stable; every substantive tool returns a structured not-implemented response. Nothing here pretends to work.

---

## What this skill WILL do

Determine whether a business qualifies for the EME sworn-affidavit route instead of a paid verification certificate, and generate the affidavit from the official dtic template ready for commissioning.

**Regulator / authority:** Department of Trade, Industry and Competition (the dtic)

## Planned tools

- `check_eme_qualification` — Check whether the business qualifies as an EME (affidavit route).
- `generate_affidavit` — Generate the sworn-affidavit document from the official dtic template.
- `get_status` — implementation status (works today, reports the scaffold honestly)

## What implementation requires (researched, not guessed)

The EME turnover threshold, start-up recognition rules and current official affidavit templates require research against the live dtic codes of good practice.

Primary sources to verify against:

- the dtic B-BBEE pages and official affidavit templates (https://www.thedtic.gov.za)

## Why the stubs are honest

Per the mia-skills ground rules: no invented regulatory numbers, no pretend automation. Each stub returns `implemented: false` with `requires_human` context and names what must be researched first. The structural tests pin this honesty.

## Run it anyway

```bash
cd skills/generate-bbbee-affidavit-south-africa
pip install -e ".[dev]"
python server.py   # exposes the stubs + get_status via MCP
```

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
