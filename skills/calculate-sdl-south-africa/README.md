# calculate-sdl-south-africa

Calculate the South African **Skills Development Levy** (SDL) and check whether an employer is liable at all.

**Status:** Alpha (v0.1.0) — fully working calculation. No external systems, no credentials.

---

## What it does

SDL is the third leg of the employer's monthly SARS payroll stool, next to PAYE and UIF (see `calculate-paye-south-africa`). This skill exposes three tools:

1. **`check_sdl_liability`** — the exemption test: expected leviable remuneration over the next 12 months vs the R500,000 threshold, plus the public-sector and exempt-organisation categories.
2. **`calculate_sdl`** — 1% of the monthly leviable amount, with an automatic flag when the annualised payroll suggests the employer may be exempt entirely.
3. **`get_status`** — implementation status and the rule basis.

---

## The rules — verified on SARS 30 July 2026

| Item | Value |
|---|---|
| Rate | **1%** of the leviable amount |
| Leviable amount | Salaries including wages, overtime payments, leave pay, bonuses, fees, commissions and lump sum payments |
| Exemption | Expected leviable remuneration over the **next 12 months** won't exceed **R500,000** |
| Also exempt | Public service employers; national/provincial public entities 80%+ Parliament-funded; PBOs with a Tax Exemption Unit letter; municipalities with a ministerial exemption certificate |

SDL is an **employer cost** — it is never deducted from employees.

---

## Worked example

Payroll of **R100,000/month** (annualises to R1.2m — liable):

| Output | Value |
|---|---|
| Monthly SDL | **R1,000.00** |

Payroll of **R30,000/month** (annualises to R360,000): the calculation returns R300.00 *and* flags that the employer is likely exempt — run `check_sdl_liability`.

---

## How to use it

```bash
cd skills/calculate-sdl-south-africa
pip install -e ".[dev]"
python server.py
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "sdl": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-sdl-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"My payroll is R85k a month across four staff. Use sdl to tell me if I owe the skills levy and how much."*

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true`:

1. SDL registration runs through the SARS employer processes alongside PAYE; monthly declaration and payment are real filings.
2. The R500,000 exemption test is forward-looking — an estimate by nature. Document it and revisit when pay or headcount changes; the tool warns when you're within 20% of the line.
3. Which pay items count as leviable for a specific payroll is practitioner territory.

---

## Rule basis and maintenance

- SARS Skills Development Levy page (last updated 15 Aug 2025), verified 30 July 2026
- Last rule check: July 2026

If SARS changes the rate or threshold, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm payroll with a professional.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
