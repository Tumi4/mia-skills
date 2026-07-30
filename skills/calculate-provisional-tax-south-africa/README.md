# calculate-provisional-tax-south-africa

Calculate South African **provisional tax (IRP6)** payments, check who has to file, compute the **basic amount**, and quantify exposure to the **20% underestimation penalty**.

**Status:** Alpha (v0.1.0) — fully working calculation. No external systems, no credentials.

---

## What it does

Provisional tax is where founders get hurt twice a year. Five tools:

1. **`check_provisional_taxpayer_status`** — who must file: companies and trusts always; natural persons unless excluded (no business income + within the 2027 tax threshold, or interest/dividends/rental/unregistered-employer income ≤ R30,000).
2. **`calculate_provisional_payment`** — period 1 (half of full-year tax less credits) and period 2 (full-year tax less credits and the first payment), for companies (27%), individuals (2027 table + age rebates) and ordinary trusts (45%).
3. **`check_underestimation_penalty`** — the rule that stings: at or below R1m actual, the estimate must reach 90% of actual *or* the basic amount; above R1m, 80% of actual. Misses cost **20%** of the shortfall — this tool quantifies it.
4. **`calculate_basic_amount`** — latest assessed taxable income less taxable capital gains, +8% when the estimate is made more than 18 months after that year end.
5. **`get_status`** — implementation status and the rule basis.

---

## The rules — verified 30 July 2026 against the current SARS guide

Everything is pinned to the **SARS Guide for Provisional Tax (GEN-PT-01-G01, effective 29 June 2026)** and the SARS provisional tax page (updated 29 June 2026):

| Rule | Value |
|---|---|
| First period | Within 6 months of year start — half of full-year tax less credits |
| Second period | Last working day of the year — full-year tax less credits and P1 |
| Accuracy test ≤ R1m | Estimate ≥ 90% of actual **or** ≥ basic amount |
| Accuracy test > R1m | Estimate ≥ 80% of actual |
| Underestimation penalty | **20%** of the shortfall vs the benchmark tax |
| Late payment penalty | 10% |
| Basic amount | Last assessed taxable income − taxable capital gain, **+8%** after 18 months |
| Status exclusions | Tax thresholds R99,000 / R153,250 / R171,300 (2027); R30,000 other-income rule |

---

## Worked example

A company that made **R800,000** but estimated **R600,000** at period 2, with a basic amount of R700,000 and R150,000 already paid:

| Output | Value |
|---|---|
| 90% of actual | R720,000 — estimate is below it |
| Basic amount | R700,000 — estimate is below it too → penalty triggered |
| Benchmark tax | min(tax on R720k, tax on R700k) = R189,000 |
| **Underestimation penalty** | **20% × (189,000 − 150,000) = R7,800** |

Had the estimate been R700,000 (the basic amount), the penalty would be **zero** — the basic-amount safe harbour. That single insight pays for the skill.

---

## How to use it

```bash
cd skills/calculate-provisional-tax-south-africa
pip install -e ".[dev]"
python server.py
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "provisional-tax": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-provisional-tax-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"My company will make about R1.4m taxable this year and paid R120k PAYE-equivalent so far. Use provisional-tax to work out my second payment and check my penalty risk if I'm off by 20%."*

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true`:

1. IRP6 submissions on eFiling and the payment deadlines are real obligations (10% late-payment penalty).
2. **Special trusts are not modelled** — their rebate treatment differs and is parked rather than guessed (`get_status.not_modelled`).
3. SARS may remit the underestimation penalty for seriously-calculated estimates — a practitioner conversation, not an automated one.
4. The basic amount's 14-day assessment rule is noted in outputs; a newer assessment changes the number.

---

## Rule basis and maintenance

- SARS Guide for Provisional Tax GEN-PT-01-G01, effective 29 June 2026 — verified 30 July 2026
- SARS provisional tax page (updated 29 June 2026) — status rules and thresholds
- 2027 individual table + rebates; 27% corporate; 45% ordinary trust — verified on SARS rate pages
- Last rule check: July 2026

If the rules or tables move, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm with a registered tax practitioner before filing.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
