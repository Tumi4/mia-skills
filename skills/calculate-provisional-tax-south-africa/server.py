"""
MIA Skill: Calculate South African provisional tax (IRP6) payments and penalty exposure.

Provisional tax is not a separate tax - it is the prepayment mechanism for income
tax by anyone who earns income other than remuneration (companies always;
individuals with business/investment/rental income above the exclusions). Two
payments a year, an optional third top-up, and a sharp 20% underestimation
penalty for getting the second-period estimate wrong.

Rules implemented (all verified 30 July 2026):
- WHO: any person receiving income other than remuneration; natural persons are
  excluded when they carry on no business AND taxable income is within the tax
  threshold (2027: R99,000 / R153,250 at 65+ / R171,300 at 75+), OR when taxable
  income from interest, foreign dividends, rental and unregistered-employer
  remuneration is not more than R30,000.
- WHEN: first period within six months of the start of the year of assessment;
  second period by the last working day of the year; optional third top-up.
- HOW MUCH: first period = half of normal tax on the estimated taxable income,
  less employees' tax and credits; second period = full-year tax less employees'
  tax, the first payment and credits.
- BASIC AMOUNT: latest assessed taxable income (at least 14 days old), less any
  taxable capital gain; escalated by 8% when the estimate is made more than 18
  months after that year of assessment ended.
- PENALTIES: 20% underestimation penalty (second period) - for actual taxable
  income of R1 million or less: triggered when the estimate is below BOTH 90% of
  actual and the basic amount; above R1 million: below 80% of actual. Late
  payments attract a 10% penalty.

Sources (verified 2026-07-30):
- https://www.sars.gov.za/types-of-tax/provisional-tax/  (who/when; exclusion
  thresholds incl. R30,000 and the 2027 tax thresholds; page updated 29 Jun 2026)
- SARS Guide for Provisional Tax GEN-PT-01-G01 (effective 29 June 2026):
  https://www.sars.gov.za/wp-content/uploads/Ops/Guides/GEN-PT-01-G01-Guide-for-Provisional-Tax-External-Guide.pdf
  (90%/80%/R1m rules, 20% underestimation penalty, basic amount + 8% escalation,
  period formulas, 10% late-payment penalty)
- https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/
  (2027 individual table + rebates)
- SARS "Companies, Trusts and SBC" rate page (27% corporate, 45% trust flat rate)

Scope note: entity types covered are company (27%), individual (2027 table with
age rebates) and ordinary trust (45% flat). Special trusts are NOT modelled -
their rebate treatment differs and is parked rather than guessed.

This is a tool, not tax advice. IRP6 filings are real submissions - always
confirm with a registered tax practitioner.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.provisional-tax")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-provisional-tax-south-africa")

# --- Constants (verified 2026-07-30) ---------------------------------------------

# 2027 individual brackets (floor, base, rate) - tax = base + rate * (income - floor).
# Source: SARS rates-for-individuals page (checked 2026-07-30).
PERSONAL_TAX_BRACKETS_2027: list[tuple[float, float, float]] = [
    (0, 0.0, 0.18),
    (245_100, 44_118.0, 0.26),
    (383_100, 79_998.0, 0.31),
    (530_200, 125_599.0, 0.36),
    (695_800, 185_215.0, 0.39),
    (887_000, 259_783.0, 0.41),
    (1_878_600, 666_339.0, 0.45),
]
PRIMARY_REBATE = 17_820.0
SECONDARY_REBATE_65_PLUS = 9_765.0
TERTIARY_REBATE_75_PLUS = 3_249.0

# 2027 tax thresholds (exclusion test for natural persons without business income).
# Source: SARS provisional tax page, updated 29 Jun 2026 (checked 2026-07-30).
TAX_THRESHOLDS_2027 = {"under_65": 99_000.0, "65_to_74": 153_250.0, "75_plus": 171_300.0}

# Natural-person exclusion: interest + foreign dividends + fixed-property rental +
# unregistered-employer remuneration not more than R30,000. Same source.
OTHER_INCOME_EXCLUSION_ZAR = 30_000.0

# Interest exemptions (informational, same source).
INTEREST_EXEMPTION_UNDER_65 = 23_800.0
INTEREST_EXEMPTION_65_PLUS = 34_500.0

# Flat rates. Source: SARS Companies/Trusts/SBC rate page (checked 2026-07-30).
CORPORATE_TAX_RATE = 0.27
TRUST_FLAT_RATE = 0.45

# Second-period estimate rules and penalties.
# Source: SARS Guide for Provisional Tax GEN-PT-01-G01, effective 29 June 2026
# (checked 2026-07-30).
UNDERESTIMATION_SPLIT_ZAR = 1_000_000.0
ACCURACY_PCT_AT_OR_BELOW_1M = 0.90
ACCURACY_PCT_ABOVE_1M = 0.80
UNDERESTIMATION_PENALTY_RATE = 0.20
LATE_PAYMENT_PENALTY_RATE = 0.10
BASIC_AMOUNT_ESCALATION_RATE = 0.08
BASIC_AMOUNT_ESCALATION_AFTER_MONTHS = 18

DEADLINES_NOTE = (
    "First period: within six months of the start of the year of assessment. "
    "Second period: no later than the last working day of the year of assessment. "
    "Optional third top-up payment thereafter (for February year-ends, the last "
    "business day of September / within six months of year end)."
)


class EntityType:
    company = "company"
    individual = "individual"
    trust = "trust"


# --- Models ---------------------------------------------------------------------


class TaxpayerStatusInput(BaseModel):
    """Inputs for the provisional-taxpayer status check (natural persons and entities)."""

    receives_income_other_than_remuneration: bool = Field(
        ...,
        description="Any income beyond salary from a registered employer (business, "
        "freelance, interest, rental, foreign dividends, etc.).",
    )
    is_natural_person: bool = Field(
        default=True,
        description="False for companies/trusts (which are provisional taxpayers when they earn income).",
    )
    carries_on_business: bool = Field(
        default=False,
        description="Natural persons only: earns income from carrying on any business.",
    )
    expected_taxable_income_zar: float = Field(
        default=0,
        ge=0,
        description="Natural persons only: expected taxable income for the year.",
    )
    other_income_zar: float = Field(
        default=0,
        ge=0,
        description="Natural persons only: taxable income from interest, foreign "
        "dividends, rental of fixed property and unregistered-employer remuneration.",
    )
    age: int = Field(default=40, ge=0, le=120)


class ProvisionalPaymentInput(BaseModel):
    """Inputs for a first- or second-period payment calculation (2027 year)."""

    period: Literal[1, 2] = Field(..., description="1 = first period, 2 = second period.")
    entity_type: Literal["company", "individual", "trust"] = "individual"
    estimated_taxable_income_zar: float = Field(..., ge=0)
    age: int = Field(default=40, ge=0, le=120, description="Individuals only - drives the rebates.")
    employees_tax_zar: float = Field(
        default=0,
        ge=0,
        description="Employees' tax (PAYE) for the relevant period: first six months "
        "for period 1; the FULL year for period 2.",
    )
    first_period_payment_zar: float = Field(
        default=0, ge=0, description="Period 2 only: the provisional tax paid at period 1."
    )
    foreign_tax_credits_zar: float = Field(default=0, ge=0)


class UnderestimationInput(BaseModel):
    """Inputs for the second-period underestimation penalty check (2027 year)."""

    actual_taxable_income_zar: float = Field(..., ge=0)
    second_period_estimate_zar: float = Field(..., ge=0)
    entity_type: Literal["company", "individual", "trust"] = "individual"
    age: int = Field(default=40, ge=0, le=120)
    employees_tax_plus_provisional_paid_zar: float = Field(
        default=0,
        ge=0,
        description="Employees' tax plus provisional tax paid for the year (the amounts "
        "credited against the penalty base).",
    )
    basic_amount_zar: float | None = Field(
        default=None,
        ge=0,
        description="The taxpayer's basic amount (use calculate_basic_amount). Needed "
        "for the at-or-below-R1m test; if omitted, only the 90% leg is evaluated and "
        "the output says so.",
    )


class BasicAmountInput(BaseModel):
    """Inputs to compute the 'basic amount' from the latest assessment."""

    last_assessed_taxable_income_zar: float = Field(
        ...,
        ge=0,
        description="Taxable income per the latest preceding assessment (issued at "
        "least 14 days before submitting the return).",
    )
    taxable_capital_gain_in_that_year_zar: float = Field(default=0, ge=0)
    months_since_end_of_that_year: int = Field(
        ...,
        ge=0,
        le=240,
        description="Full months between the end of that year of assessment and when this estimate is made.",
    )


# --- Helpers --------------------------------------------------------------------


def _bracket_tax(amount: float, brackets: list[tuple[float, float, float]]) -> float:
    tax = 0.0
    for floor, base, rate in brackets:
        if amount > floor:
            tax = base + rate * (amount - floor)
    return tax


def _rebates_for_age(age: int) -> float:
    total = PRIMARY_REBATE
    if age >= 65:
        total += SECONDARY_REBATE_65_PLUS
    if age >= 75:
        total += TERTIARY_REBATE_75_PLUS
    return total


def _annual_tax(entity_type: str, taxable_income: float, age: int) -> float:
    """Normal tax on taxable income for the 2027 year, by entity type."""
    if entity_type == EntityType.company:
        return taxable_income * CORPORATE_TAX_RATE
    if entity_type == EntityType.trust:
        return taxable_income * TRUST_FLAT_RATE
    return max(0.0, _bracket_tax(taxable_income, PERSONAL_TAX_BRACKETS_2027) - _rebates_for_age(age))


def _threshold_for_age(age: int) -> float:
    if age >= 75:
        return TAX_THRESHOLDS_2027["75_plus"]
    if age >= 65:
        return TAX_THRESHOLDS_2027["65_to_74"]
    return TAX_THRESHOLDS_2027["under_65"]


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def check_provisional_taxpayer_status(input: TaxpayerStatusInput) -> dict:
    """Check whether a person must register/file as a provisional taxpayer.

    Applies the SARS tests (provisional tax page, updated 29 June 2026): any
    person receiving income other than remuneration is a provisional taxpayer,
    EXCEPT a natural person who carries on no business and whose taxable income
    is within the tax threshold for their age, OR whose interest/foreign
    dividends/rental/unregistered-employer income is not more than R30,000.
    """
    logger.info("check_provisional_taxpayer_status: natural=%s", input.is_natural_person)

    if not input.receives_income_other_than_remuneration:
        return {
            "is_provisional_taxpayer": False,
            "reason": "Only remuneration income - provisional tax does not apply.",
            "deadlines": "",
            "requires_human": True,
            "notes": "If non-salary income starts (side business, rental, large "
            "interest), re-check - status can change mid-year.",
        }

    if not input.is_natural_person:
        return {
            "is_provisional_taxpayer": True,
            "reason": "Companies and trusts earning income are provisional taxpayers.",
            "deadlines": DEADLINES_NOTE,
            "requires_human": True,
            "notes": "File IRP6 returns for both periods even in loss years - a nil "
            "estimate is still a filing.",
        }

    threshold = _threshold_for_age(input.age)
    exclusions = []
    if not input.carries_on_business and input.expected_taxable_income_zar <= threshold:
        exclusions.append(
            f"No business income and taxable income (R{input.expected_taxable_income_zar:,.0f}) "
            f"within the R{threshold:,.0f} tax threshold for age {input.age}."
        )
    if input.other_income_zar <= OTHER_INCOME_EXCLUSION_ZAR and not input.carries_on_business:
        exclusions.append(
            f"Interest/foreign dividends/rental/unregistered-employer income "
            f"(R{input.other_income_zar:,.0f}) is not more than "
            f"R{OTHER_INCOME_EXCLUSION_ZAR:,.0f}."
        )

    is_provisional = len(exclusions) == 0
    return {
        "is_provisional_taxpayer": is_provisional,
        "reason": (
            "Receives non-remuneration income and no exclusion applies."
            if is_provisional
            else "Excluded: " + " ".join(exclusions)
        ),
        "deadlines": DEADLINES_NOTE if is_provisional else "",
        "interest_exemption_note": (
            f"Interest exemptions: R{INTEREST_EXEMPTION_UNDER_65:,.0f} under 65, "
            f"R{INTEREST_EXEMPTION_65_PLUS:,.0f} at 65+."
        ),
        "requires_human": True,
        "notes": "Confirm edge cases (capital gains, mixed income) with a practitioner.",
    }


@mcp.tool()
async def calculate_provisional_payment(input: ProvisionalPaymentInput) -> dict:
    """Calculate a first- or second-period provisional tax payment (2027 year).

    Per the SARS guide: period 1 = half of the normal tax on the estimated
    taxable income, less employees' tax for the period and foreign credits;
    period 2 = the full-year tax, less employees' tax for the year, the first
    payment and credits. Floored at zero.

    Entity types: company (27%), individual (2027 table with age rebates),
    ordinary trust (45%). Special trusts are not modelled.
    """
    logger.info(
        "calculate_provisional_payment: period=%s type=%s est=%s",
        input.period,
        input.entity_type,
        input.estimated_taxable_income_zar,
    )

    annual_tax = _annual_tax(input.entity_type, input.estimated_taxable_income_zar, input.age)

    if input.period == 1:
        payable = max(0.0, annual_tax / 2 - input.employees_tax_zar - input.foreign_tax_credits_zar)
        formula = "half of full-year tax, less employees' tax for the period and credits"
    else:
        payable = max(
            0.0,
            annual_tax
            - input.employees_tax_zar
            - input.first_period_payment_zar
            - input.foreign_tax_credits_zar,
        )
        formula = "full-year tax, less employees' tax for the year, the first-period payment and credits"

    return {
        "period": input.period,
        "tax_year": "2027 (1 March 2026 - 28 February 2027 for Feb year-ends)",
        "entity_type": input.entity_type,
        "estimated_taxable_income_zar": round(input.estimated_taxable_income_zar, 2),
        "full_year_tax_zar": round(annual_tax, 2),
        "provisional_payment_zar": round(payable, 2),
        "formula": formula,
        "deadlines": DEADLINES_NOTE,
        "requires_human": True,
        "human_steps": [
            "Submit the IRP6 return on eFiling and pay by the deadline - a 10% penalty "
            "applies to late payments",
            "For the second period, sanity-check the estimate against the 90%/80% "
            "accuracy rules (use check_underestimation_penalty)",
            "Confirm the estimate and any credits with a registered tax practitioner",
        ],
        "warnings": [
            "Estimate-based: the real IRP6 uses your actual estimate and SARS-recorded "
            "credits. Special trusts are not modelled by this tool."
        ],
    }


@mcp.tool()
async def check_underestimation_penalty(input: UnderestimationInput) -> dict:
    """Check exposure to the 20% second-period underestimation penalty (2027 year).

    Per the SARS guide (GEN-PT-01-G01, effective 29 June 2026):
    - Actual taxable income of R1 million or less: penalty applies when the
      estimate is below BOTH 90% of actual AND the basic amount. Penalty = 20%
      of (the lesser of tax on 90%-of-actual and tax on the basic amount, less
      employees' tax + provisional tax paid).
    - Actual above R1 million: penalty applies when the estimate is below 80% of
      actual. Penalty = 20% of (tax on 80%-of-actual, less amounts paid).
    """
    actual = input.actual_taxable_income_zar
    estimate = input.second_period_estimate_zar
    paid = input.employees_tax_plus_provisional_paid_zar

    def tax_on(amount: float) -> float:
        return _annual_tax(input.entity_type, amount, input.age)

    warnings: list[str] = []

    if actual <= UNDERESTIMATION_SPLIT_ZAR:
        ninety_of_actual = ACCURACY_PCT_AT_OR_BELOW_1M * actual
        below_90 = estimate < ninety_of_actual
        if input.basic_amount_zar is None:
            triggered = below_90
            if below_90:
                warnings.append(
                    "Basic amount not supplied - the at-or-below-R1m test requires the "
                    "estimate to be below BOTH 90% of actual AND the basic amount. "
                    "Result shown assumes the basic-amount leg also fails; supply "
                    "basic_amount_zar (see calculate_basic_amount) to confirm."
                )
            penalty_base_tax = tax_on(ninety_of_actual)
        else:
            below_basic = estimate < input.basic_amount_zar
            triggered = below_90 and below_basic
            penalty_base_tax = min(tax_on(ninety_of_actual), tax_on(input.basic_amount_zar))
        rule = "at-or-below R1m: estimate must reach 90% of actual or the basic amount"
    else:
        eighty_of_actual = ACCURACY_PCT_ABOVE_1M * actual
        triggered = estimate < eighty_of_actual
        penalty_base_tax = tax_on(eighty_of_actual)
        rule = "above R1m: estimate must reach 80% of actual"

    penalty = max(0.0, UNDERESTIMATION_PENALTY_RATE * (penalty_base_tax - paid)) if triggered else 0.0

    return {
        "rule_applied": rule,
        "actual_taxable_income_zar": round(actual, 2),
        "second_period_estimate_zar": round(estimate, 2),
        "penalty_triggered": triggered,
        "estimated_penalty_zar": round(penalty, 2),
        "penalty_rate": UNDERESTIMATION_PENALTY_RATE,
        "warnings": warnings,
        "requires_human": True,
        "notes": (
            "SARS may remit the penalty on request where the estimate was seriously "
            "calculated and not deliberately understated - practitioner territory. "
            "Late payments separately attract a 10% penalty."
        ),
    }


@mcp.tool()
async def calculate_basic_amount(input: BasicAmountInput) -> dict:
    """Compute the 'basic amount' from the latest preceding assessment.

    Per the SARS guide: the latest assessed taxable income (assessment issued at
    least 14 days before the return is submitted), LESS any taxable capital gain
    in that assessment, escalated by 8% when the estimate is made more than 18
    months after the end of that year of assessment.
    """
    base = max(
        0.0,
        input.last_assessed_taxable_income_zar - input.taxable_capital_gain_in_that_year_zar,
    )
    escalated = input.months_since_end_of_that_year > BASIC_AMOUNT_ESCALATION_AFTER_MONTHS
    basic = base * (1 + BASIC_AMOUNT_ESCALATION_RATE) if escalated else base

    return {
        "basic_amount_zar": round(basic, 2),
        "escalation_applied": escalated,
        "escalation_rule": (
            f"+{BASIC_AMOUNT_ESCALATION_RATE:.0%} because the estimate is made more than "
            f"{BASIC_AMOUNT_ESCALATION_AFTER_MONTHS} months after that year end"
            if escalated
            else "no escalation (within 18 months)"
        ),
        "requires_human": True,
        "notes": (
            "The assessment must be at least 14 days old when the return is submitted; "
            "a newer assessment changes the basic amount. Confirm with a practitioner."
        ),
    }


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-provisional-tax-south-africa",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": (
            "SARS Guide for Provisional Tax GEN-PT-01-G01 (effective 29 Jun 2026): "
            "period formulas, 90%/80%/R1m second-period accuracy rules, 20% "
            "underestimation penalty, basic amount + 8% escalation, 10% late-payment "
            "penalty; SARS provisional tax page (29 Jun 2026): status exclusions; "
            "2027 individual table + 27% corporate + 45% trust rates"
        ),
        "tools_working": [
            "check_provisional_taxpayer_status",
            "calculate_provisional_payment",
            "check_underestimation_penalty",
            "calculate_basic_amount",
            "get_status",
        ],
        "tools_stubbed": [],
        "not_modelled": "Special trusts (rebate treatment differs - parked, not guessed)",
        "disclaimer": "Calculation tool, not tax advice. IRP6 filings are real "
        "submissions - confirm with a registered tax practitioner.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
