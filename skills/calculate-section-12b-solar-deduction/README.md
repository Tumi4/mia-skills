# calculate-section-12b-solar-deduction

Calculate the South African **Section 12B** renewable-energy (solar PV) tax deduction and the real cash saving for a business taxpayer.

**Status:** Alpha (v0.1.0) — fully working calculation. No external systems, no credentials.

---

## What it does

Section 12B of the Income Tax Act gives a business a **100% year-one deduction** on the cost of qualifying renewable-energy generation assets (for solar PV, with no capacity cap). This skill turns that rule into four callable tools:

1. **`calculate_deduction`** — the headline. Give it equipment cost, taxpayer type, and taxable income; it returns the deduction, the real cash tax saving, and the effective net cost of the system after the tax benefit.
2. **`compare_12b_vs_12ba`** — shows the live 12B (100%) benefit against the expired 12BA (125%) so founders understand what's still available.
3. **`check_eligibility`** — walks the core SARS eligibility conditions and returns a clear pass/fail with reasons.
4. **`get_status`** — implementation status and the rule basis.

---

## Why this skill

Most South African business owners don't realise that commercial solar effectively pays for a large chunk of itself through Section 12B. A R650,000 solar system for a profitable company returns about **R175,500 in cash tax saving** — bringing the effective net cost down to roughly R574,500. This skill makes that calculation instant and explainable, right inside whatever AI tool the founder already uses.

It's also directly aligned with MIA's climate-sector focus: every climate founder evaluating solar is a candidate for this.

---

## Important: 12B vs 12BA (current as of 2026)

- **Section 12B (100% year-one PV deduction)** — **LIVE.** Permanent legislation, no expiry.
- **Section 12BA (enhanced 125% deduction)** — **EXPIRED 28 February 2025.** Not renewed in the 2025 Budget. Assets brought into use after that date do **not** qualify for the 125% rate.

This skill calculates the live 12B benefit and can show what 12BA *would* have given, clearly flagged as expired. (The earlier Section 12J VCC regime is also closed — sunset 30 June 2021 — and is not covered here.)

---

## How to use it

### As a standalone MCP server

```bash
cd skills/calculate-section-12b-solar-deduction
pip install -e ".[dev]"
python server.py
```

### From Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "section-12b": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-section-12b-solar-deduction/server.py"]
    }
  }
}
```

Then ask Claude: *"A client is installing a R650,000 commercial solar system, they're a company with R3m taxable income. Use section-12b to calculate their tax benefit."*

---

## Worked example

Input: R650,000 equipment + R100,000 labour, company, R3,000,000 taxable income.

| Output | Value |
|---|---|
| Section applied | Section 12B (100%) |
| Qualifying cost | R650,000 |
| Deduction | R650,000 |
| Cash tax saving | R175,500 |
| Total project cost | R750,000 |
| Effective net cost | R574,500 |

(Labour is excluded from the deduction but included in total project cost.)

---

## Taxpayer types & rates

The cash tax saving is computed at the correct rate for the taxpayer:

| `taxpayer_type` | Rate basis |
|---|---|
| `company` | Flat 27% |
| `individual` | Progressive 2026 individual brackets (relief at the marginal rate) |
| `sole_proprietor` | Progressive individual brackets (taxed as an individual) |
| `trust` | **Flat 45%** — ordinary (non-special) trusts |
| `special_trust` | Progressive individual brackets (e.g. disability / testamentary minor trusts) |

For flat-rate taxpayers (company, ordinary trust) the saving is capped at the income available to absorb the deduction; any excess becomes an assessed loss carried forward rather than an immediate cash saving.

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true` with these steps:

1. Obtain a valid Certificate of Compliance (CoC) from a registered electrician — without it, SARS rejects the claim.
2. Itemise equipment separately from labour on the invoice — 12B does not apply to labour.
3. Confirm the commissioning date falls in the intended tax year.
4. Have a registered tax practitioner confirm the claim before filing.

Other limits:
- Only renewable sources qualify (solar PV, wind, hydro, concentrated solar, biomass). Diesel/gas/petrol do not.
- The taxpayer must own the asset (or hold it under an instalment credit agreement). Operating-lease equipment is claimed by the lessor.
- Residential/personal use does not qualify under 12B (the individual solar rebate s6C ended after the 2024 tax year).
- Grant-funded portions don't qualify — only own-funded equipment.
- Standalone batteries (without PV) sit in a SARS grey area and are treated case-by-case.

---

## Rule basis and maintenance

- Income Tax Act s12B (live), s12BA (expired 28 Feb 2025)
- Personal tax brackets: 2026 year of assessment
- Corporate rate: 27%
- Ordinary trust rate: 45% (special trusts taxed on the individual brackets)
- Last rule check: June 2026

If SARS changes rates or brackets, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm with a registered tax practitioner before filing.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
