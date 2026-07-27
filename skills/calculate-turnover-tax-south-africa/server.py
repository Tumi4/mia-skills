"""
MIA Skill: Calculate South African turnover tax for micro businesses.

Turnover tax is the simplified tax system for micro businesses under the Sixth
Schedule to the Income Tax Act (No. 58 of 1962). For a registered micro business it
REPLACES income tax, VAT, provisional tax, capital gains tax and dividends tax, and
is levied on taxable TURNOVER (receipts), not profit.

IMPORTANT context (current as of July 2026):
- Budget 2026 changed this regime materially. The qualifying annual turnover limit
  increased from R1 million to R2.3 million (SARS: "The effective date for the
  increase is 1 April 2026") and the tax-free band moved from R335,000 to R600,000
  for the 2027 year of assessment (1 March 2026 - 28 February 2027).
- Because tax is charged on turnover, a LOSS-MAKING business still pays turnover
  tax. The compare_vs_standard_tax tool makes this trade-off explicit.

This skill is PURE CALCULATION over published SARS rules. No external systems, no
browser automation, no credentials. It is deterministic and fully testable.

Sources (all verified 27 July 2026):
- https://www.sars.gov.za/tax-rates/turnover-tax/  (2027 + 2026 rate tables)
- https://www.sars.gov.za/types-of-tax/turnover-tax/  (R2.3m qualifying limit,
  effective date, eligible entity types, what turnover tax replaces)
- https://www.sars.gov.za/faq/faq-who-does-not-qualify-to-be-registered-for-turnover-tax/
  (disqualification rules)
- https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/
  (2027 individual brackets + primary rebate, used by the comparison tool)
- https://www.sars.gov.za/tax-rates/income-tax/companies-trusts-and-small-business-corporations-sbc/
  (27% corporate rate and 2027 SBC table, used by the comparison tool)

This is a tool, not tax advice. Always have a registered tax practitioner confirm.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.turnover-tax")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-turnover-tax-south-africa")

# --- Constants (SARS rules, verified 2026-07-27) --------------------------------

# Turnover tax tables. Tuple = (band_floor, base_tax, marginal_rate):
#   tax = base_tax + marginal_rate * (taxable_turnover - band_floor)
# for the highest band whose floor is below the taxable turnover. Turnover at or
# below the first floor is tax-free.
#
# Source: https://www.sars.gov.za/tax-rates/turnover-tax/ (checked 2026-07-27).
# NOTE: the SARS overview page words the 2027 third band as "2% of the amount
# above 600 000"; the rates page says "above 950 000". The rates page is the
# arithmetically consistent one (3,500 = 1% of the full 600k-950k band, and
# 12,500 = 3,500 + 2% of the full 950k-1.4m band), so its formulas are used here.
TURNOVER_TAX_TABLES: dict[int, list[tuple[float, float, float]]] = {
    # 2027 year of assessment: 1 March 2026 - 28 February 2027 (post-Budget 2026).
    2027: [
        (600_000, 0.0, 0.01),
        (950_000, 3_500.0, 0.02),
        (1_400_000, 12_500.0, 0.03),
    ],
    # 2026 year of assessment: 1 March 2025 - 28 February 2026 (pre-Budget 2026).
    2026: [
        (335_000, 0.0, 0.01),
        (500_000, 1_650.0, 0.02),
        (750_000, 6_650.0, 0.03),
    ],
}

YEAR_OF_ASSESSMENT_LABELS = {
    2027: "1 March 2026 - 28 February 2027",
    2026: "1 March 2025 - 28 February 2026",
}

# Qualifying annual turnover limit per year of assessment.
# 2027: R2.3m (Budget 2026 increase; SARS: "The effective date for the increase is
#       1 April 2026"). 2026: R1m (pre-Budget 2026).
# Source: https://www.sars.gov.za/types-of-tax/turnover-tax/ (checked 2026-07-27).
QUALIFYING_TURNOVER_LIMIT: dict[int, float] = {2027: 2_300_000.0, 2026: 1_000_000.0}

# Disqualification threshold: "more than 20% of the receipts are derived from
# rendering a professional service".
# Source: SARS FAQ "Who does not qualify to be registered for Turnover Tax?"
# (page last updated 25 Feb 2021; checked 2026-07-27).
PROFESSIONAL_SERVICE_RECEIPTS_LIMIT_PCT = 20.0

# --- Comparison constants (verified 2026-07-27) ---------------------------------

# Corporate income tax rate, years of assessment ending 1 Apr 2026 - 31 Mar 2027.
# Source: SARS "Companies, Trusts and SBC" rate page (checked 2026-07-27).
CORPORATE_TAX_RATE = 0.27

# 2027 individual brackets (1 March 2026 - 28 February 2027), same tuple shape.
# Source: https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/
# (checked 2026-07-27).
PERSONAL_TAX_BRACKETS_2027: list[tuple[float, float, float]] = [
    (0, 0.0, 0.18),
    (245_100, 44_118.0, 0.26),
    (383_100, 79_998.0, 0.31),
    (530_200, 125_599.0, 0.36),
    (695_800, 185_215.0, 0.39),
    (887_000, 259_783.0, 0.41),
    (1_878_600, 666_339.0, 0.45),
]

# Primary rebate, 2027 year of assessment (under-65 taxpayers).
PRIMARY_REBATE_2027 = 17_820.0

# 2027 Small Business Corporation table (years ending 1 Apr 2026 - 31 Mar 2027).
# Taxable income at or below R99,000 is tax-free for a qualifying SBC.
# Source: SARS "Companies, Trusts and SBC" rate page (checked 2026-07-27).
SBC_BRACKETS_2027: list[tuple[float, float, float]] = [
    (99_000, 0.0, 0.07),
    (365_000, 18_620.0, 0.21),
    (550_000, 57_470.0, 0.27),
]


class EntityType(StrEnum):
    """Entity types that may register for turnover tax (SARS overview page)."""

    sole_proprietor = "sole_proprietor"
    partnership = "partnership"
    close_corporation = "close_corporation"
    company = "company"
    cooperative = "cooperative"


# --- Models ---------------------------------------------------------------------


class TurnoverTaxInput(BaseModel):
    """Inputs to calculate turnover tax for a micro business."""

    annual_turnover_zar: float = Field(
        ...,
        ge=0,
        description="Taxable turnover (business receipts) for the year of assessment, in rand.",
    )
    tax_year: Literal[2026, 2027] = Field(
        default=2027,
        description="Year of assessment: 2027 = 1 Mar 2026 - 28 Feb 2027 (current), "
        "2026 = 1 Mar 2025 - 28 Feb 2026 (pre-Budget 2026 table).",
    )


class TurnoverTaxOutput(BaseModel):
    success: bool
    tax_year: int
    year_of_assessment: str
    taxable_turnover_zar: float
    turnover_tax_zar: float
    effective_rate: float
    band_applied: str
    exceeds_qualifying_limit: bool
    qualifying_limit_zar: float
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


class EligibilityInput(BaseModel):
    """Inputs for the turnover tax qualification check.

    Covers the qualifying turnover limit plus the disqualification rules published
    on the SARS FAQ. It does NOT cover every Sixth Schedule edge rule - see the
    `not_checked` field in the result.
    """

    annual_turnover_zar: float = Field(..., ge=0)
    entity_type: EntityType = Field(default=EntityType.sole_proprietor)
    professional_service_receipts_percent: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage of total receipts derived from rendering a professional "
        "service (e.g. legal, accounting, medical, consulting).",
    )
    is_personal_service_provider_or_labour_broker: bool = Field(
        default=False,
        description="True if the taxpayer is a personal service provider or a labour broker.",
    )
    holds_shares_in_unlisted_companies: bool = Field(
        default=False,
        description="True if the owner holds shares in any unlisted company.",
    )
    company_year_end_february: bool = Field(
        default=True,
        description="Companies/CCs/co-ops only: financial year end falls on 28 February.",
    )
    all_shareholders_natural_persons: bool = Field(
        default=True,
        description="Companies/CCs/co-ops only: every shareholder/member is a natural person.",
    )
    tax_year: Literal[2026, 2027] = 2027


class CompareInput(BaseModel):
    """Inputs to compare turnover tax against the standard tax regimes."""

    annual_turnover_zar: float = Field(..., ge=0)
    estimated_annual_expenses_zar: float = Field(
        ...,
        ge=0,
        description="Estimated tax-deductible business expenses for the year. Needed "
        "because standard tax is charged on PROFIT while turnover tax is charged on "
        "TURNOVER.",
    )
    entity_type: EntityType = Field(
        default=EntityType.sole_proprietor,
        description="company/close_corporation/cooperative use the corporate 27% rate "
        "(plus an SBC view); sole_proprietor/partnership use the 2027 individual table.",
    )


# --- Helpers --------------------------------------------------------------------


def _bracket_tax(amount: float, brackets: list[tuple[float, float, float]]) -> float:
    """Tax under a (floor, base, rate) marginal table: base + rate * (amount - floor)
    for the highest floor below amount. Amounts at or below the first floor pay the
    table's implied minimum (0 where the first tuple is a zero-rate floor)."""
    tax = 0.0
    for floor, base, rate in brackets:
        if amount > floor:
            tax = base + rate * (amount - floor)
    return tax


def _band_description(turnover: float, tax_year: int) -> str:
    table = TURNOVER_TAX_TABLES[tax_year]
    first_floor = table[0][0]
    if turnover <= first_floor:
        return f"R0 - R{first_floor:,.0f}: 0% (tax-free band)"
    applicable = table[0]
    for band in table:
        if turnover > band[0]:
            applicable = band
    floor, base, rate = applicable
    if base:
        return f"R{base:,.0f} + {rate:.0%} of turnover above R{floor:,.0f}"
    return f"{rate:.0%} of turnover above R{floor:,.0f}"


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def calculate_turnover_tax(input: TurnoverTaxInput) -> TurnoverTaxOutput:
    """Calculate South African turnover tax for a micro business.

    Applies the SARS turnover tax table for the chosen year of assessment (default
    2027: R600,000 tax-free, then 1% / 2% / 3% marginal bands) to the taxable
    turnover, and reports the effective rate and the band applied.

    Limits and notes:
    - Turnover tax is charged on receipts, not profit - a loss-making business still
      pays it. Use compare_vs_standard_tax to sanity-check the regime choice.
    - The qualifying annual turnover limit for 2027 is R2.3m (Budget 2026 increase;
      SARS gives 1 April 2026 as the effective date for the increase). Above the
      limit the business does not qualify; the figure returned is what the table
      would produce, with a clear warning.
    - Registration (SARS form TT01) and timing rules apply and are not automated here.
    """
    logger.info("calculate_turnover_tax: turnover=%s year=%s", input.annual_turnover_zar, input.tax_year)

    warnings: list[str] = []
    turnover = input.annual_turnover_zar
    limit = QUALIFYING_TURNOVER_LIMIT[input.tax_year]

    tax = _bracket_tax(turnover, TURNOVER_TAX_TABLES[input.tax_year])
    effective_rate = (tax / turnover) if turnover > 0 else 0.0

    exceeds = turnover > limit
    if exceeds:
        warnings.append(
            f"Turnover of R{turnover:,.0f} exceeds the R{limit:,.0f} qualifying annual "
            f"turnover limit for the {input.tax_year} year of assessment - the business "
            "does not qualify for turnover tax at this level. The figure shown is what "
            "the table would produce; standard tax will apply instead."
        )

    return TurnoverTaxOutput(
        success=True,
        tax_year=input.tax_year,
        year_of_assessment=YEAR_OF_ASSESSMENT_LABELS[input.tax_year],
        taxable_turnover_zar=round(turnover, 2),
        turnover_tax_zar=round(tax, 2),
        effective_rate=round(effective_rate, 4),
        band_applied=_band_description(turnover, input.tax_year),
        exceeds_qualifying_limit=exceeds,
        qualifying_limit_zar=limit,
        requires_human=True,
        human_steps=[
            "Register for turnover tax with SARS (form TT01 / eFiling) - registration "
            "windows apply; check the SARS turnover tax page for current timing",
            "Confirm with a registered tax practitioner that turnover tax beats standard "
            "tax for this business (it taxes turnover even in loss-making years)",
            "Keep records of all receipts - taxable turnover is receipts-based",
        ],
        notes=(
            f"Turnover tax for the {input.tax_year} year of assessment "
            f"({YEAR_OF_ASSESSMENT_LABELS[input.tax_year]}): R{tax:,.2f} on taxable "
            f"turnover of R{turnover:,.0f} ({effective_rate:.2%} effective). Turnover tax "
            "replaces income tax, VAT, provisional tax, CGT and dividends tax for a "
            "registered micro business."
        ),
        warnings=warnings,
    )


@mcp.tool()
async def check_eligibility(input: EligibilityInput) -> dict:
    """Check whether a business qualifies to register for turnover tax.

    Walks the qualifying turnover limit plus the disqualification rules published on
    the SARS FAQ ("Who does not qualify to be registered for Turnover Tax?"):
    unlisted-company shareholding, >20% professional-service receipts, personal
    service providers / labour brokers, and (for companies) a non-February year end
    or non-natural-person shareholders.

    HONESTY LIMIT: the Sixth Schedule contains further edge rules (e.g. around
    disposals of capital assets over a multi-year window and multi-partnership
    membership) that this tool does NOT check - they are listed in `not_checked`
    and require a practitioner or further research.
    """
    logger.info("check_eligibility: turnover=%s type=%s", input.annual_turnover_zar, input.entity_type)

    blockers: list[str] = []
    limit = QUALIFYING_TURNOVER_LIMIT[input.tax_year]

    if input.annual_turnover_zar > limit:
        blockers.append(
            f"Annual turnover R{input.annual_turnover_zar:,.0f} exceeds the qualifying "
            f"limit of R{limit:,.0f} for the {input.tax_year} year of assessment."
        )
    if input.professional_service_receipts_percent > PROFESSIONAL_SERVICE_RECEIPTS_LIMIT_PCT:
        blockers.append(
            f"More than {PROFESSIONAL_SERVICE_RECEIPTS_LIMIT_PCT:.0f}% of receipts "
            f"({input.professional_service_receipts_percent:.0f}%) are derived from "
            "rendering a professional service (SARS FAQ disqualification)."
        )
    if input.is_personal_service_provider_or_labour_broker:
        blockers.append("Personal service providers and labour brokers do not qualify (SARS FAQ).")
    if input.holds_shares_in_unlisted_companies:
        blockers.append("Shares are held in an unlisted company - this disqualifies the taxpayer (SARS FAQ).")

    is_corporate = input.entity_type in (
        EntityType.company,
        EntityType.close_corporation,
        EntityType.cooperative,
    )
    if is_corporate and not input.company_year_end_february:
        blockers.append(
            "The company's financial year end is not 28 February (SARS FAQ requires a "
            "February year end for companies on turnover tax)."
        )
    if is_corporate and not input.all_shareholders_natural_persons:
        blockers.append(
            "Not all of the company's shareholders are natural persons (SARS FAQ disqualification)."
        )

    eligible = len(blockers) == 0
    return {
        "eligible_on_checked_rules": eligible,
        "entity_type": input.entity_type,
        "blockers": blockers,
        "checks_performed": [
            f"Qualifying turnover limit (R{limit:,.0f}, {input.tax_year} year)",
            "Professional-service receipts <= 20% of total receipts",
            "Not a personal service provider or labour broker",
            "No shareholding in unlisted companies",
            "Companies: 28 February year end",
            "Companies: all shareholders are natural persons",
        ],
        "not_checked": [
            "Sixth Schedule limits on disposals of capital assets over a multi-year "
            "window - requires research/practitioner confirmation",
            "Multi-partnership membership rules for partners - requires research/practitioner confirmation",
        ],
        "next_step": (
            "All checked rules pass. Confirm the not_checked items with a registered "
            "tax practitioner, then register via SARS form TT01."
            if eligible
            else "Resolve the blockers above or remain on the standard tax system."
        ),
    }


@mcp.tool()
async def compare_vs_standard_tax(input: CompareInput) -> dict:
    """Compare turnover tax against the standard tax regime for the same figures.

    The honest comparison a founder actually needs: turnover tax is charged on
    TURNOVER; standard tax is charged on PROFIT (turnover minus deductible
    expenses). This tool computes both, using the 2027 tables:
    - company / close_corporation / cooperative: corporate 27% flat, plus the SBC
      table shown separately (SBC has its own eligibility rules - confirm those).
    - sole_proprietor / partnership: 2027 individual brackets less the primary
      rebate (under-65; partners compare on their own profit share).

    Key edge it exposes: a LOSS-MAKING business pays R0 standard tax but still pays
    turnover tax on its receipts.
    """
    turnover = input.annual_turnover_zar
    expenses = input.estimated_annual_expenses_zar
    profit = turnover - expenses

    turnover_tax = _bracket_tax(turnover, TURNOVER_TAX_TABLES[2027])

    is_corporate = input.entity_type in (
        EntityType.company,
        EntityType.close_corporation,
        EntityType.cooperative,
    )
    taxable_profit = max(0.0, profit)
    if is_corporate:
        standard_regime = "Corporate income tax at 27% on profit (2027)"
        standard_tax = taxable_profit * CORPORATE_TAX_RATE
    else:
        standard_regime = (
            "2027 individual brackets on profit, less the primary rebate "
            f"(R{PRIMARY_REBATE_2027:,.0f}, under-65)"
        )
        standard_tax = max(
            0.0, _bracket_tax(taxable_profit, PERSONAL_TAX_BRACKETS_2027) - PRIMARY_REBATE_2027
        )

    warnings: list[str] = []
    if profit <= 0 and turnover_tax > 0:
        warnings.append(
            f"This business is loss-making (profit R{profit:,.0f}) yet would still pay "
            f"R{turnover_tax:,.2f} turnover tax, because turnover tax is charged on "
            "receipts. Standard tax would be R0."
        )

    result: dict = {
        "annual_turnover_zar": round(turnover, 2),
        "estimated_expenses_zar": round(expenses, 2),
        "profit_zar": round(profit, 2),
        "turnover_tax": {
            "tax_zar": round(turnover_tax, 2),
            "effective_rate_on_turnover": round(turnover_tax / turnover, 4) if turnover else 0.0,
            "note": "2027 table; replaces income tax, VAT, provisional tax, CGT and "
            "dividends tax for a registered micro business.",
        },
        "standard_tax": {
            "regime": standard_regime,
            "tax_zar": round(standard_tax, 2),
            "effective_rate_on_profit": round(standard_tax / profit, 4) if profit > 0 else 0.0,
        },
        "cheaper_option": "turnover_tax" if turnover_tax < standard_tax else "standard_tax",
        "saving_zar": round(abs(standard_tax - turnover_tax), 2),
        "warnings": warnings,
        "takeaway": (
            "Turnover tax wins on high-margin micro businesses under the R2.3m limit; "
            "standard tax wins on thin margins or losses. VAT input credits and other "
            "deductions are outside this comparison - confirm the final choice with a "
            "registered tax practitioner."
        ),
    }

    if is_corporate:
        sbc_tax = _bracket_tax(taxable_profit, SBC_BRACKETS_2027)
        result["sbc_alternative"] = {
            "tax_zar": round(sbc_tax, 2),
            "note": "2027 Small Business Corporation table (R99,000 tax-free, then "
            "7%/21%/27%). SBC status has its own eligibility rules not checked here.",
        }

    return result


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-turnover-tax-south-africa",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": (
            "Sixth Schedule to the Income Tax Act (turnover tax); SARS 2027 + 2026 "
            "rate tables; Budget 2026 threshold increase to R2.3m (SARS effective "
            "date 1 April 2026)"
        ),
        "tools_working": [
            "calculate_turnover_tax",
            "check_eligibility",
            "compare_vs_standard_tax",
            "get_status",
        ],
        "tools_stubbed": [],
        "tax_year_tables": "2027 (1 Mar 2026 - 28 Feb 2027) current; 2026 retained",
        "qualifying_limit_zar": QUALIFYING_TURNOVER_LIMIT[2027],
        "disclaimer": "Calculation tool, not tax advice. Confirm with a registered tax practitioner.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
