# calculate-turnover-tax-south-africa

Calculate South African **turnover tax** for micro businesses, check qualification, and compare it honestly against the standard tax regime.

**Status:** Alpha (v0.1.0) — fully working calculation. No external systems, no credentials.

---

## What it does

Turnover tax (Sixth Schedule to the Income Tax Act) is the simplified regime for micro businesses. For a registered micro business it **replaces income tax, VAT, provisional tax, capital gains tax and dividends tax** — and it is charged on **turnover (receipts), not profit**. This skill turns those rules into four callable tools:

1. **`calculate_turnover_tax`** — the headline. Give it annual taxable turnover; it returns the tax, the effective rate, and the band applied, for the 2027 (current) or 2026 year of assessment.
2. **`check_eligibility`** — walks the qualifying turnover limit and the SARS-published disqualification rules, with an explicit list of what it does *not* check.
3. **`compare_vs_standard_tax`** — the decision tool: turnover tax (on turnover) vs standard tax (on profit), including the loss-making trap and an SBC view for companies.
4. **`get_status`** — implementation status and the rule basis.

---

## Budget 2026 changed this regime — the numbers you remember are probably stale

- **Qualifying annual turnover limit: R1 million → R2.3 million.** SARS: *"The effective date for the increase is 1 April 2026."*
- **Tax-free band: R335,000 → R600,000** for the 2027 year of assessment.

**2027 table (1 March 2026 – 28 February 2027), verified on SARS 27 July 2026:**

| Taxable turnover | Tax |
|---|---|
| R0 – R600,000 | 0% |
| R600,001 – R950,000 | 1% of turnover above R600,000 |
| R950,001 – R1,400,000 | R3,500 + 2% of turnover above R950,000 |
| R1,400,001 + | R12,500 + 3% of turnover above R1,400,000 |

The pre-Budget 2026 table is retained under `tax_year=2026` for prior-year work.

*(Note: SARS's overview page words the third band as "2% of the amount above 600 000" while the rates page says "above 950 000". The rates-page formula is the arithmetically consistent one — R3,500 is exactly 1% of the full R600k–950k band — and is what this skill implements. Both pages are cited in `server.py`.)*

---

## Worked example

A micro business with **R1,000,000** turnover in the 2027 year:

| Output | Value |
|---|---|
| Turnover tax | **R4,500** (R3,500 + 2% of R50,000) |
| Effective rate on turnover | 0.45% |
| Exceeds qualifying limit? | No (limit is R2.3m) |

Same business under the old 2026 table would have paid **R14,150** — Budget 2026 cut this micro business's tax by more than two-thirds.

---

## The honest comparison founders actually need

`compare_vs_standard_tax` takes turnover **and estimated expenses**, because the regimes tax different bases:

- High-margin micro businesses usually win on turnover tax (R1m turnover / R50k profit: turnover tax R4,500 vs corporate tax R13,500).
- Thin-margin or **loss-making businesses still pay turnover tax** — R800k turnover at a loss still owes R2,000, where standard tax owes R0. The tool warns about this explicitly.
- Companies also get the 2027 **SBC table** as a side-by-side view (SBC has its own eligibility rules, not checked here).

---

## How to use it

### As a standalone MCP server

```bash
cd skills/calculate-turnover-tax-south-africa
pip install -e ".[dev]"
python server.py
```

### From Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "turnover-tax": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/calculate-turnover-tax-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"My spaza-adjacent distribution business turned over R1.4m this year with about R1.1m in costs. Use turnover-tax to tell me if the micro-business regime beats standard tax."*

---

## Eligibility rules covered (and not covered)

Checked, per the SARS FAQ "Who does not qualify to be registered for Turnover Tax?":

- Annual turnover within the qualifying limit (R2.3m for 2027)
- Not more than 20% of receipts from rendering a professional service
- Not a personal service provider or labour broker
- No shareholding in unlisted companies
- Companies: financial year end on 28 February
- Companies: all shareholders are natural persons

**Not checked** (returned explicitly in `not_checked`): Sixth Schedule limits on multi-year capital asset disposals and multi-partnership membership rules. Confirm these with a registered tax practitioner.

---

## Limits and human-required steps

This is a **calculation tool, not tax advice.** It always returns `requires_human: true`:

1. Registration for turnover tax (SARS form TT01 / eFiling) is a real filing with timing windows — not automated here.
2. The regime choice is sticky and consequential (it replaces VAT participation too) — confirm with a registered tax practitioner.
3. The eligibility check is explicit about the rules it does not cover.

---

## Rule basis and maintenance

- Sixth Schedule to the Income Tax Act (turnover tax)
- SARS turnover tax rate tables: 2027 (current) and 2026, verified 27 July 2026
- Qualifying limit R2.3m per Budget 2026 (SARS effective date: 1 April 2026)
- Comparison tool: 2027 individual brackets + primary rebate, 27% corporate rate, 2027 SBC table (all verified 27 July 2026)
- Last rule check: July 2026

If SARS changes rates or brackets, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm with a registered tax practitioner before electing a tax regime.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
