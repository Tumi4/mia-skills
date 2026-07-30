# calculate-carbon-tax-south-africa

Calculate South African **carbon tax** from emissions and the entity's allowance, sanity-check scope, and estimate the carbon fuel levy hiding in fleet fuel spend.

**Status:** Alpha (v0.2.0) — working calculation, promoted from scaffold on 30 July 2026. No external systems, no credentials.

---

## What it does

Carbon tax is the climate lever in the SARS toolbox and squarely in MIA's climate lane. Four tools:

1. **`calculate_carbon_tax`** — tonnes CO2e × the year's rate × (1 − total allowance %). Rates pinned to the National Treasury Budget 2026 Review: **R308/t for 2026**, R236/t for 2025.
2. **`check_liability`** — honest scope guidance: maps what you attest about emissions-generating activities and capacity, and is explicit that the activity-specific Schedule 2 thresholds are *not* encoded (`not_checked`).
3. **`estimate_carbon_fuel_levy`** — the carbon component in pump prices (19c/l petrol, 23c/l diesel from 1 April 2026) applied to monthly fleet litres. Clearly flagged as already-in-the-price awareness, not a separate payment.
4. **`get_status`** — implementation status and the rule basis.

---

## Why the allowance is an input, not a constant

SARS states industry-specific tax-free allowances range **60%–95%**. The actual combination — basic, trade exposure, performance, carbon budget, offsets — is an entity-specific determination. Encoding per-component percentages without a live primary source would violate this library's no-invented-numbers rule, so the tool takes the **total allowance as a bounded input** (0–95%, default 60%) and flags the determination as practitioner territory.

---

## Worked example

**1,000 t CO2e in 2026 with the 60% typical minimum allowance:**

| Output | Value |
|---|---|
| Headline rate | R308/t |
| Effective rate after allowance | R123.20/t |
| Gross | R308,000 |
| **Carbon tax payable** | **R123,200.00** |

At the 95% maximum allowance the same emissions cost R15,400. A fleet burning 1,000 l petrol + 1,000 l diesel a month carries **R420/month** of carbon fuel levy inside its fuel bill.

---

## How to use it

```bash
cd skills/calculate-carbon-tax-south-africa
pip install -e ".[dev]"
python server.py
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "carbon-tax": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-carbon-tax-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"Our plant emitted 4,200 tonnes CO2e this year and our practitioner says our total allowance is 70%. Use carbon-tax to work out the bill."*

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true`:

1. Emissions facilities must be licensed with SARS (customs and excise administration).
2. The allowance determination and any offset usage are practitioner territory.
3. Emissions tonnage must come from formal GHG reporting by a competent person — this tool never estimates emissions.
4. Schedule 2 activity thresholds are not encoded (`check_liability` says so explicitly rather than guessing).

---

## Rule basis and maintenance

- National Treasury, Budget 2026 Review, Ch. 4: R236 → **R308/t CO2e from 1 January 2026**; carbon fuel levy 19c/23c per litre from 1 April 2026 — verified 30 July 2026
- SARS carbon tax page: allowance range 60%–95%, liability scope wording (page dated Dec 2024 — stale for rates, which is why Treasury is the rate source)
- Last rule check: July 2026. **The rate escalates annually — re-verify every budget cycle.**

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Confirm with a registered tax practitioner and an emissions professional.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
