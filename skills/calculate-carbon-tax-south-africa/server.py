"""
MIA Skill: Calculate South African carbon tax liability.

Carbon tax (Carbon Tax Act, 2019) is levied per tonne of CO2-equivalent emissions
on entities that operate emissions-generating facilities at or above the carbon
tax threshold. The headline rate escalates annually - which is exactly why this
skill refuses to rely on memory and pins its constants to the National Treasury
Budget 2026 Review.

IMPORTANT context (current as of July 2026):
- Rate: R308 per tonne CO2e from 1 January 2026 (up from R236 in 2025).
- Industry-specific tax-free allowances range from 60% to 95% per SARS - the
  entity-specific combination (basic, trade exposure, performance, carbon
  budget, offsets) is a practitioner determination, so this tool takes the total
  allowance as a bounded INPUT rather than pretending to derive it.
- The carbon FUEL levy (the carbon component inside the general fuel levy,
  already included in pump prices) rises to 19c/l petrol and 23c/l diesel from
  1 April 2026.

This skill is PURE CALCULATION over published rates. No external systems, no
credentials. Emissions licensing, reporting and allowance determinations are
real processes flagged requires_human.

Sources (verified 30 July 2026):
- National Treasury, Budget 2026 Review, Ch. 4 (Revenue trends and tax proposals):
  https://www.treasury.gov.za/documents/National%20Budget/2026/review/Chapter%204.pdf
  ("increased from R236 to R308 per tonne of carbon dioxide equivalent from
  1 January 2026"; carbon fuel levy "19c/litre for petrol and 23c/litre for
  diesel from 1 April 2026")
- SARS carbon tax page (allowances "ranging from 60 per cent to 95 per cent";
  liability scope wording; page last updated 13 Dec 2024 - stale for rates,
  which is why Treasury is the rate source):
  https://www.sars.gov.za/customs-and-excise/excise/environmental-levy-products/carbon-tax/

This is a tool, not tax advice. Confirm with a registered tax practitioner and
an emissions professional.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.carbon-tax")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-carbon-tax-south-africa")

# --- Constants (verified 2026-07-30) ---------------------------------------------

# Headline carbon tax rate per tonne CO2e by calendar year.
# Source: National Treasury Budget 2026 Review Ch.4 (checked 2026-07-30):
# "increased from R236 to R308 per tonne of carbon dioxide equivalent from
# 1 January 2026". The rate escalates annually - re-verify every budget cycle.
CARBON_TAX_RATE_PER_TONNE: dict[int, float] = {
    2026: 308.0,
    2025: 236.0,
}

# Industry-specific tax-free allowance range per SARS ("ranging from 60 per cent
# to 95 per cent"). The entity's actual combination of basic / trade-exposure /
# performance / carbon-budget / offset allowances is a practitioner
# determination - this skill accepts the total as input, capped at 95%.
ALLOWANCE_TYPICAL_MIN_PCT = 60.0
ALLOWANCE_MAX_PCT = 95.0

# Carbon fuel levy (the carbon component inside the general fuel levy, already
# included in pump prices) from 1 April 2026.
# Source: Treasury Budget 2026 Review Ch.4 (checked 2026-07-30).
CARBON_FUEL_LEVY_PETROL_PER_LITRE = 0.19
CARBON_FUEL_LEVY_DIESEL_PER_LITRE = 0.23

# --- Models ---------------------------------------------------------------------


class CarbonTaxInput(BaseModel):
    """Inputs for the carbon tax calculation."""

    tonnes_co2e: float = Field(
        ...,
        ge=0,
        description="Taxable greenhouse gas emissions for the period, in tonnes of "
        "CO2-equivalent (from the entity's emissions reporting).",
    )
    total_allowance_percent: float = Field(
        default=ALLOWANCE_TYPICAL_MIN_PCT,
        ge=0,
        le=ALLOWANCE_MAX_PCT,
        description="The entity's TOTAL tax-free allowance percentage (basic + trade "
        "exposure + performance + carbon budget + offsets), as determined with a "
        "practitioner. SARS indicates industry-specific allowances range from 60% "
        "to 95%; default is the 60% typical minimum.",
    )
    calendar_year: Literal[2025, 2026] = Field(
        default=2026,
        description="Calendar year of the emissions (rates differ: 2025 = R236/t, 2026 = R308/t).",
    )


class CarbonTaxOutput(BaseModel):
    success: bool
    calendar_year: int
    tonnes_co2e: float
    headline_rate_per_tonne_zar: float
    total_allowance_percent: float
    effective_rate_per_tonne_zar: float
    gross_carbon_tax_zar: float
    carbon_tax_payable_zar: float
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


class LiabilityInput(BaseModel):
    """Inputs for the carbon tax scope check (honest guidance, not a ruling)."""

    conducts_emissions_generating_activities: bool = Field(
        ...,
        description="The entity operates fuel-combustion / industrial-process / "
        "fugitive-emissions facilities.",
    )
    capacity_at_or_above_schedule_threshold: bool | None = Field(
        default=None,
        description="Combined installed capacity is at or above the Carbon Tax Act "
        "Schedule 2 threshold for the activity. Leave empty if unknown - the "
        "activity-specific thresholds must be checked against Schedule 2.",
    )


class FuelLevyInput(BaseModel):
    """Inputs for the carbon fuel levy cost estimate."""

    monthly_petrol_litres: float = Field(default=0, ge=0)
    monthly_diesel_litres: float = Field(default=0, ge=0)


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def calculate_carbon_tax(input: CarbonTaxInput) -> CarbonTaxOutput:
    """Calculate South African carbon tax from emissions and the entity's allowance.

    tax = tonnes CO2e x rate for the year x (1 - total allowance %).
    Rates: R308/t for 2026, R236/t for 2025 (National Treasury Budget 2026).

    Limits and notes:
    - The total allowance is an INPUT because the basic / trade-exposure /
      performance / carbon-budget / offset combination is entity-specific and
      must be determined with a practitioner (SARS range: 60%-95%).
    - Emissions figures must come from proper GHG reporting by a competent
      person; this tool does not estimate emissions.
    """
    logger.info(
        "calculate_carbon_tax: tonnes=%s allowance=%s year=%s",
        input.tonnes_co2e,
        input.total_allowance_percent,
        input.calendar_year,
    )

    rate = CARBON_TAX_RATE_PER_TONNE[input.calendar_year]
    effective_rate = rate * (1 - input.total_allowance_percent / 100)
    gross = input.tonnes_co2e * rate
    payable = input.tonnes_co2e * effective_rate

    warnings = [
        "The total allowance percentage is entity-specific (basic, trade exposure, "
        "performance, carbon budget, offsets) and must be confirmed with a "
        "practitioner - this calculation applies the percentage you supplied.",
        "The carbon tax rate escalates annually - re-verify the rate for any year "
        "not listed in this skill's constants.",
    ]
    if input.total_allowance_percent < ALLOWANCE_TYPICAL_MIN_PCT:
        warnings.append(
            f"Allowance below the {ALLOWANCE_TYPICAL_MIN_PCT:.0f}% typical minimum "
            "indicated by SARS - double-check the determination."
        )

    return CarbonTaxOutput(
        success=True,
        calendar_year=input.calendar_year,
        tonnes_co2e=round(input.tonnes_co2e, 3),
        headline_rate_per_tonne_zar=rate,
        total_allowance_percent=input.total_allowance_percent,
        effective_rate_per_tonne_zar=round(effective_rate, 2),
        gross_carbon_tax_zar=round(gross, 2),
        carbon_tax_payable_zar=round(payable, 2),
        requires_human=True,
        human_steps=[
            "License emissions facilities with SARS (carbon tax is administered "
            "through the customs and excise system)",
            "Confirm the entity's allowance determination and offset usage with a "
            "registered tax practitioner",
            "Source emissions tonnage from the entity's formal GHG reporting "
            "(competent person / DFFE reporting requirements)",
        ],
        notes=(
            f"Carbon tax for {input.calendar_year}: {input.tonnes_co2e:,.0f} t CO2e at "
            f"R{rate:,.0f}/t with a {input.total_allowance_percent:.0f}% allowance = "
            f"R{payable:,.2f} payable (effective R{effective_rate:,.2f}/t)."
        ),
        warnings=warnings,
    )


@mcp.tool()
async def check_liability(input: LiabilityInput) -> dict:
    """Check whether an entity is likely within carbon tax scope (honest guidance).

    Per SARS, liability applies to entities operating emissions-generating
    facilities at a combined installed capacity at or above the carbon tax
    threshold for the activity. The activity-specific Schedule 2 thresholds are
    NOT encoded here (requires research) - this tool maps what you attest to and
    is explicit about what it did not check.
    """
    if not input.conducts_emissions_generating_activities:
        likely = "out_of_scope"
        detail = "No emissions-generating activities attested - carbon tax does not apply."
    elif input.capacity_at_or_above_schedule_threshold is True:
        likely = "likely_liable"
        detail = (
            "Emissions-generating activities at/above the activity threshold - "
            "licensing and carbon tax accounts likely required."
        )
    elif input.capacity_at_or_above_schedule_threshold is False:
        likely = "likely_below_threshold"
        detail = (
            "Activities exist but attested below the activity threshold - likely out "
            "of scope, but confirm against Schedule 2 for each activity."
        )
    else:
        likely = "unknown_needs_schedule_2_check"
        detail = (
            "Capacity vs the Schedule 2 threshold is unknown - check the Carbon Tax "
            "Act Schedule 2 for the specific activity thresholds."
        )

    return {
        "scope_assessment": likely,
        "detail": detail,
        "not_checked": [
            "Activity-specific Schedule 2 capacity thresholds (requires research "
            "against the Carbon Tax Act / DFFE guidance - not encoded here)",
        ],
        "requires_human": True,
        "next_step": (
            "Confirm scope with a practitioner; if liable, use calculate_carbon_tax "
            "with the entity's determined allowance."
        ),
    }


@mcp.tool()
async def estimate_carbon_fuel_levy(input: FuelLevyInput) -> dict:
    """Estimate the carbon fuel levy embedded in monthly petrol/diesel spend.

    From 1 April 2026 the carbon fuel levy is 19c/l petrol and 23c/l diesel
    (Treasury Budget 2026). IMPORTANT: this is already included in pump prices -
    it is an awareness figure for fleet cost analysis, NOT a separate payment.
    """
    petrol_cost = input.monthly_petrol_litres * CARBON_FUEL_LEVY_PETROL_PER_LITRE
    diesel_cost = input.monthly_diesel_litres * CARBON_FUEL_LEVY_DIESEL_PER_LITRE
    total = petrol_cost + diesel_cost

    return {
        "monthly_petrol_litres": input.monthly_petrol_litres,
        "monthly_diesel_litres": input.monthly_diesel_litres,
        "petrol_levy_zar": round(petrol_cost, 2),
        "diesel_levy_zar": round(diesel_cost, 2),
        "total_carbon_fuel_levy_zar": round(total, 2),
        "rates": "19c/l petrol, 23c/l diesel from 1 April 2026 (Treasury Budget 2026)",
        "important": (
            "This levy is already included in pump prices - an awareness figure for "
            "fleet cost analysis, not an additional payment to SARS."
        ),
    }


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-carbon-tax-south-africa",
        "version": "0.2.0",
        "status": "alpha",
        "rule_basis": (
            "Carbon Tax Act (2019): R308/t CO2e from 1 Jan 2026 (R236/t for 2025) per "
            "National Treasury Budget 2026 Review; allowances 60%-95% per SARS "
            "(entity-specific combination taken as input); carbon fuel levy 19c/23c "
            "per litre from 1 Apr 2026"
        ),
        "tools_working": [
            "calculate_carbon_tax",
            "check_liability",
            "estimate_carbon_fuel_levy",
            "get_status",
        ],
        "tools_stubbed": [],
        "rate_2026_per_tonne_zar": CARBON_TAX_RATE_PER_TONNE[2026],
        "not_encoded": "Schedule 2 activity thresholds and per-allowance percentages "
        "(entity-specific / requires research)",
        "disclaimer": "Calculation tool, not tax advice. Confirm with a practitioner "
        "and an emissions professional.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
