# check-vat-registration-south-africa

Determine whether a South African business **must** register for VAT, **may** register voluntarily, or can't yet — and estimate a simple VAT payable/refund position at the current rate.

**Status:** Alpha (v0.1.0) — fully working determination/calculation. No external systems, no credentials.

---

## What it does

VAT registration is one of the first compliance cliffs a growing South African business hits — and Budget 2026 just moved the cliff. This skill exposes three tools:

1. **`check_registration_required`** — the determination. Give it the past-12-month taxable supplies (and optionally the expected next 12 months); it returns mandatory / voluntary-available / not-yet-eligible, the 21-business-day deadline note when registration is compulsory, and honest transitional warnings.
2. **`estimate_vat_position`** — simple net-VAT estimate: output VAT on standard-rated sales less input VAT on vatable purchases, at 15%.
3. **`get_status`** — implementation status and the rule basis.

---

## Budget 2026 moved the thresholds — verified on SARS 27 July 2026

| Test | Current rule (from 1 April 2026) | Previous rule |
|---|---|---|
| **Compulsory** | Taxable supplies in any consecutive 12-month period **exceeded or likely to exceed R2.3 million** → register within **21 business days** | R1 million |
| **Voluntary** | Past-12-month taxable supplies **exceed R120,000** | R50,000 |
| **VAT rate** | **15%** — the 2025 Budget's proposed 15.5% / 16% increases were **reversed by legislation on 24 April 2025** | 15% |

Below R120,000, alternative voluntary routes exist (R4,200/month patterns, written contracts over R120k, capital expenditure over R120k, General Notice R446/R447 activities) — the tool lists them rather than pretending they don't exist.

**Transitional honesty:** a business sitting between R1m and R2.3m today gets an explicit warning that the old R1m rule applied before 1 April 2026 — if it crossed R1m before that date, an obligation may already have arisen. Practitioner check flagged.

---

## Worked example

A business with **R2.4m** of taxable supplies in the past 12 months:

| Output | Value |
|---|---|
| `registration_type` | `mandatory` |
| Deadline | Within 21 business days of exceeding R2.3m |

A quarter with **R1,000,000** standard-rated sales (excl. VAT) and **R600,000** vatable purchases (excl. VAT):

| Output | Value |
|---|---|
| Output VAT | R150,000 |
| Input VAT | R90,000 |
| **Net VAT payable** | **R60,000** |

---

## How to use it

### As a standalone MCP server

```bash
cd skills/check-vat-registration-south-africa
pip install -e ".[dev]"
python server.py
```

### From Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vat-registration": {
      "command": "python",
      "args": ["/path/to/mia-skills/skills/check-vat-registration-south-africa/server.py"]
    }
  }
}
```

Then ask Claude: *"We did R1.8m in the last 12 months and just signed contracts worth R3m for next year. Use vat-registration to tell me if we have to register."*

---

## Limits and human-required steps

This is a **determination tool, not tax advice.** It always returns `requires_human: true`:

1. The actual registration is a real SARS filing (eFiling or branch) — not automated here.
2. "Taxable supplies" classification (exempt vs zero-rated vs standard) changes the answer — practitioner territory.
3. The VAT position tool is deliberately simple: it does **not** model zero-rated exports, exempt supplies, apportionment, or denied inputs (entertainment, most passenger vehicles). It says so in its output.

---

## Rule basis and maintenance

- VAT registration tests as published by SARS (register-for-VAT page, updated 17 June 2026): compulsory > R2.3m / 21 business days; voluntary > R120,000; both effective 1 April 2026 per Budget 2026
- VAT rate 15% (SARS VAT page, updated 14 May 2026; 2025 proposed increases reversed 24 April 2025)
- Last rule check: July 2026

If SARS changes the thresholds or the rate, update the constants at the top of `server.py` and bump the version. The tests pin the reference numbers so drift is caught.

---

## Liability

Provided as-is under Apache 2.0. A tool, not tax advice. Always confirm with a registered tax practitioner before registering or filing.

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
