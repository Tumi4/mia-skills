# calculate-paye-south-africa

Calculate monthly **PAYE**, the **UIF** employee contribution and **take-home pay** for a South African salary — 2027 year of assessment (1 March 2026 – 28 February 2027).

**Status:** Alpha (v0.1.0) — fully working calculation. No external systems, no credentials.

---

## What it does

Every employer in South Africa has to get PAYE right every month. This skill exposes three tools:

1. **`calculate_monthly_paye`** — the headline. Monthly salary + age (+ optional medical scheme member count) in; monthly PAYE, UIF (employee and employer 1% each), medical tax credit effect, and take-home pay out.
2. **`calculate_annual_summary`** — the same computation viewed annually: total tax, total take-home, effective rate.
3. **`get_status`** — implementation status and the rule basis.

Method: **annualisation** — annual tax on 12× the monthly salary via the 2027 table, less age-based rebates, less the Medical Scheme Fees Tax Credit, ÷ 12, floored at zero.

---

## 2027 constants — all verified on live SARS pages, 27 July 2026

The 2027 numbers **changed from 2026** (brackets, rebates, thresholds and medical credits all moved). This skill does not reuse stale constants:

| Item | 2027 value |
|---|---|
| Brackets | 18% → 45%, top bracket above R1,878,600 |
| Primary rebate | R17,820 |
| Secondary rebate (65+) | R9,765 |
| Tertiary rebate (75+) | R3,249 |
| Tax thresholds | R99,000 / R153,250 (65+) / R171,300 (75+) |
| Medical Scheme Fees Tax Credit | R376 pm (member), R752 pm (member + 1), +R254 pm each additional |
| UIF | 1% employee + 1% employer, remuneration ceiling **R17,712 pm** (max R177.12) — ceiling in effect since 1 June 2021 |

---

## Worked example

**R30,000/month, age 40, family of three on medical aid:**

| Output | Value |
|---|---|
| Annual tax before rebates | R73,992.00 |
| Primary rebate | −R17,820.00 |
| Medical tax credit (annual) | −R12,072.00 |
| **Monthly PAYE** | **R3,675.00** |
| UIF (employee) | R177.12 (capped) |
| **Monthly take-home** | **R26,147.88** |

Same salary with no medical aid: monthly PAYE R4,681.00. At age 65 (no medical aid): R3,867.25 — the secondary rebate at work.

---

## How to use it

### As a standalone MCP server

```bash
cd skills/calculate-paye-south-africa
pip install -e ".[dev]"
python server.py
```

### From Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "paye": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-paye-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"I'm hiring my first employee at R22,000 a month, she's 31 with two kids on her medical aid. Use paye to work out what lands in her account and what I owe SARS."*

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true`:

1. Employer PAYE registration with SARS, monthly declarations and payment deadlines are real obligations — not automated here.
2. UIF registration with the Department of Employment and Labour is a separate obligation from the SARS-collected contributions.
3. Scope is a **stable monthly cash salary**: bonuses, travel and other allowances, fringe benefits, retirement-fund deductions and variable pay all change the answer — payroll-provider territory. SDL (an employer levy) is out of scope. SARS's published deduction tables may differ by a few rand due to income bucketing.

---

## Rule basis and maintenance

- 2027 individual tax table, rebates and thresholds — SARS rates-for-individuals page, verified 27 July 2026
- 2027 Medical Scheme Fees Tax Credit — SARS medical-tax-credit page, verified 27 July 2026
- UIF 1% + 1%, R17,712 pm ceiling (from 1 June 2021) — SARS UIF page (updated 15 Aug 2025), verified 27 July 2026
- Last rule check: July 2026

If SARS changes any of these, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm payroll with a professional.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
