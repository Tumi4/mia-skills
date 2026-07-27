"""
MIA Skill: Check South African VAT registration obligations.

Determines whether a business MUST register for VAT (compulsory), MAY register
(voluntary), or cannot yet register, and gives a simple VAT payable/refund
estimate at the current rate.

IMPORTANT context (current as of July 2026):
- The VAT rate is 15%. The increases proposed in the 2025 Budget (15.5% from
  1 May 2025, 16% from 1 April 2026) were REVERSED by legislation introduced on
  24 April 2025 - the rate never moved.
- Budget 2026 raised the registration thresholds with effect from 1 April 2026:
  compulsory registration R1 million -> R2.3 million of taxable supplies in any
  consecutive 12-month period; voluntary registration minimum R50,000 -> R120,000.
- Compulsory registration must be submitted within 21 business days of the date
  the R2.3 million is (or will be) exceeded.

This skill is PURE DETERMINATION/CALCULATION over published SARS rules. No
external systems, no credentials. The actual registration is a real SARS filing
and is always flagged requires_human.

Sources (all verified 27 July 2026):
- https://www.sars.gov.za/types-of-tax/value-added-tax/  (15% rate; 2025 rate-increase
  reversal; thresholds and their 1 April 2026 effective date)
- https://www.sars.gov.za/types-of-tax/value-added-tax/register-for-vat/  (compulsory
  test wording "exceeded or is likely to exceed R2.3 million"; 21 business days;
  voluntary minimum "exceeded R120 000 in the past period of 12 months"; alternative
  voluntary routes incl. General Notices R446/R447)

This is a tool, not tax advice. Always have a registered tax practitioner confirm.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.vat-registration")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-check-vat-registration-south-africa")

# --- Constants (SARS rules, verified 2026-07-27) --------------------------------

# Standard VAT rate. The 2025 Budget's proposed increases (15.5% from 1 May 2025,
# 16% from 1 April 2026) were reversed by legislation introduced 24 April 2025.
# Source: https://www.sars.gov.za/types-of-tax/value-added-tax/ (checked 2026-07-27).
VAT_RATE = 0.15

# Compulsory registration: taxable supplies in any consecutive 12-month period
# "exceeded or is likely to exceed R2.3 million". Raised from R1m effective
# 1 April 2026 (Budget 2026).
# Source: https://www.sars.gov.za/types-of-tax/value-added-tax/register-for-vat/
# (checked 2026-07-27).
MANDATORY_REGISTRATION_THRESHOLD_ZAR = 2_300_000.0
PREVIOUS_MANDATORY_THRESHOLD_ZAR = 1_000_000.0  # pre-1 April 2026, for transitional warnings
THRESHOLD_EFFECTIVE_DATE = "1 April 2026"

# Compulsory registration deadline: "within 21 business days from the date the
# R2.3 million is or will be exceeded".
REGISTRATION_DEADLINE_BUSINESS_DAYS = 21

# Voluntary registration: allowed once taxable supplies "exceeded R120 000 in the
# past period of 12 months" (below the compulsory threshold). Raised from R50,000
# effective 1 April 2026 (Budget 2026).
VOLUNTARY_REGISTRATION_MINIMUM_ZAR = 120_000.0

# Alternative voluntary routes exist below R120k (surfaced in notes, not automated):
# monthly supplies > R4,200 patterns, written contracts promising R120k+ in the
# next 12 months, capital expenditure / finance agreements over R120k, and the
# General Notice R446 activity list / R447 conditions (e.g. municipalities,
# welfare organisations, agriculture, mining, manufacturing, property and
# infrastructure development, beneficiation).
ALTERNATIVE_VOLUNTARY_ROUTES = [
    "Only 1 month traded: monthly taxable supplies exceeding R4,200",
    "2-11 months traded: average monthly taxable supplies exceeding R4,200",
    "Written contracts promising more than R120,000 of taxable supplies in the next 12 months",
    "Capital expenditure or finance agreements exceeding R120,000",
    "Activities/conditions under General Notices R446 / R447 (e.g. municipalities, welfare "
    "organisations, agriculture, mining, manufacturing, property or infrastructure development)",
]

# --- Models ---------------------------------------------------------------------


class RegistrationCheckInput(BaseModel):
    """Inputs for the VAT registration determination."""

    rolling_12m_taxable_supplies_zar: float = Field(
        ...,
        ge=0,
        description="Value of taxable supplies made in the past consecutive 12-month period, in rand.",
    )
    expected_next_12m_taxable_supplies_zar: float | None = Field(
        default=None,
        ge=0,
        description="Expected taxable supplies for the coming 12 months (the 'likely "
        "to exceed' leg of the compulsory test). Omit if unknown.",
    )
    is_non_resident_electronic_services_supplier: bool = Field(
        default=False,
        description="True for foreign suppliers of electronic services to South African "
        "customers - the same R2.3m threshold applies, tested at each month end.",
    )


class RegistrationCheckOutput(BaseModel):
    success: bool
    registration_type: str  # "mandatory" | "voluntary_available" | "not_yet_eligible"
    registration_required: bool
    voluntary_registration_available: bool
    mandatory_threshold_zar: float
    voluntary_minimum_zar: float
    thresholds_effective: str
    deadline_note: str = ""
    requires_human: bool = True
    human_steps: list[str] = []
    alternative_voluntary_routes: list[str] = []
    notes: str = ""
    warnings: list[str] = []


class VatPositionInput(BaseModel):
    """Inputs for a simple VAT payable/refund estimate (amounts EXCLUDING VAT)."""

    standard_rated_sales_excl_vat_zar: float = Field(
        ...,
        ge=0,
        description="Standard-rated sales for the period, excluding VAT.",
    )
    vatable_purchases_excl_vat_zar: float = Field(
        ...,
        ge=0,
        description="Purchases/expenses carrying claimable input VAT for the period, excluding VAT.",
    )


class VatPositionOutput(BaseModel):
    success: bool
    vat_rate: float
    output_vat_zar: float
    input_vat_zar: float
    net_vat_zar: float
    position: str  # "payable" | "refund" | "nil"
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def check_registration_required(input: RegistrationCheckInput) -> RegistrationCheckOutput:
    """Determine whether a business must (or may) register for South African VAT.

    Applies the SARS tests current from 1 April 2026:
    - COMPULSORY: taxable supplies in any consecutive 12-month period exceeded, or
      are likely to exceed, R2.3 million. Registration must be submitted within 21
      business days of that date.
    - VOLUNTARY: available once past-12-month taxable supplies exceed R120,000
      (alternative routes below that are listed in the output, not automated).

    Limits and notes:
    - "Taxable supplies" excludes exempt supplies - classification questions need a
      practitioner.
    - Transitional edge: before 1 April 2026 the compulsory threshold was R1m. A
      business that crossed R1m before that date gets an explicit warning to check
      its position.
    """
    logger.info(
        "check_registration_required: past12m=%s expected=%s",
        input.rolling_12m_taxable_supplies_zar,
        input.expected_next_12m_taxable_supplies_zar,
    )

    past = input.rolling_12m_taxable_supplies_zar
    expected = input.expected_next_12m_taxable_supplies_zar
    warnings: list[str] = []

    past_exceeds = past > MANDATORY_REGISTRATION_THRESHOLD_ZAR
    expected_exceeds = expected is not None and expected > MANDATORY_REGISTRATION_THRESHOLD_ZAR
    mandatory = past_exceeds or expected_exceeds

    voluntary_available = (not mandatory) and past > VOLUNTARY_REGISTRATION_MINIMUM_ZAR

    if mandatory:
        registration_type = "mandatory"
        basis = (
            "past 12-month taxable supplies"
            if past_exceeds
            else "expected taxable supplies for the coming 12 months"
        )
        deadline_note = (
            f"Compulsory: {basis} exceed R{MANDATORY_REGISTRATION_THRESHOLD_ZAR:,.0f}. "
            f"Submit the registration within {REGISTRATION_DEADLINE_BUSINESS_DAYS} business "
            "days of the date the threshold is (or will be) exceeded."
        )
    elif voluntary_available:
        registration_type = "voluntary_available"
        deadline_note = ""
    else:
        registration_type = "not_yet_eligible"
        deadline_note = ""

    # Transitional honesty: the pre-1 April 2026 threshold was R1m.
    if not mandatory and PREVIOUS_MANDATORY_THRESHOLD_ZAR < past <= MANDATORY_REGISTRATION_THRESHOLD_ZAR:
        warnings.append(
            f"Past 12-month supplies of R{past:,.0f} are under today's R2.3m threshold but "
            f"over the R1m threshold that applied before {THRESHOLD_EFFECTIVE_DATE}. If the "
            "R1m mark was crossed before that date, a registration obligation may already "
            "have arisen under the old rule - confirm the transitional position with a "
            "registered tax practitioner."
        )

    if input.is_non_resident_electronic_services_supplier:
        warnings.append(
            "Non-resident electronic services suppliers: compulsory registration arises at "
            "the end of the month in which total taxable supplies exceed R2.3 million - the "
            "12-month mechanics differ from resident vendors; confirm specifics with a "
            "practitioner."
        )

    human_steps = [
        "Complete the VAT registration on SARS eFiling (or at a SARS branch) - this tool "
        "does not file anything",
        "Confirm what counts as 'taxable supplies' for this business (exempt and zero-rated "
        "classification) with a registered tax practitioner",
    ]
    if registration_type == "voluntary_available":
        human_steps.insert(
            0,
            "Weigh voluntary registration: charging output VAT vs claiming input VAT - "
            "practitioner advice recommended",
        )

    notes = (
        f"Thresholds current from {THRESHOLD_EFFECTIVE_DATE} (Budget 2026): compulsory above "
        f"R{MANDATORY_REGISTRATION_THRESHOLD_ZAR:,.0f} in any consecutive 12-month period "
        f"(previously R{PREVIOUS_MANDATORY_THRESHOLD_ZAR:,.0f}); voluntary once past-12-month "
        f"supplies exceed R{VOLUNTARY_REGISTRATION_MINIMUM_ZAR:,.0f} (previously R50,000)."
    )
    if registration_type == "not_yet_eligible":
        notes += (
            " Below the voluntary minimum, alternative registration routes may still apply - "
            "see alternative_voluntary_routes."
        )

    return RegistrationCheckOutput(
        success=True,
        registration_type=registration_type,
        registration_required=mandatory,
        voluntary_registration_available=voluntary_available,
        mandatory_threshold_zar=MANDATORY_REGISTRATION_THRESHOLD_ZAR,
        voluntary_minimum_zar=VOLUNTARY_REGISTRATION_MINIMUM_ZAR,
        thresholds_effective=THRESHOLD_EFFECTIVE_DATE,
        deadline_note=deadline_note,
        requires_human=True,
        human_steps=human_steps,
        alternative_voluntary_routes=(
            ALTERNATIVE_VOLUNTARY_ROUTES if registration_type == "not_yet_eligible" else []
        ),
        notes=notes,
        warnings=warnings,
    )


@mcp.tool()
async def estimate_vat_position(input: VatPositionInput) -> VatPositionOutput:
    """Estimate the net VAT payable or refundable for a period at the current 15% rate.

    output VAT = 15% of standard-rated sales (excl. VAT);
    input VAT = 15% of vatable purchases (excl. VAT);
    net = output - input (positive = payable to SARS, negative = refund due).

    Limits and notes:
    - A deliberately SIMPLE estimate: it assumes everything is standard-rated and
      claimable. Zero-rated/exempt supplies, apportionment, and denied inputs
      (e.g. entertainment, most passenger vehicles) are not modelled.
    - Actual VAT201 returns must be prepared from proper records.
    """
    logger.info(
        "estimate_vat_position: sales=%s purchases=%s",
        input.standard_rated_sales_excl_vat_zar,
        input.vatable_purchases_excl_vat_zar,
    )

    output_vat = input.standard_rated_sales_excl_vat_zar * VAT_RATE
    input_vat = input.vatable_purchases_excl_vat_zar * VAT_RATE
    net = output_vat - input_vat

    if net > 0:
        position = "payable"
    elif net < 0:
        position = "refund"
    else:
        position = "nil"

    return VatPositionOutput(
        success=True,
        vat_rate=VAT_RATE,
        output_vat_zar=round(output_vat, 2),
        input_vat_zar=round(input_vat, 2),
        net_vat_zar=round(net, 2),
        position=position,
        requires_human=True,
        human_steps=[
            "Prepare the actual VAT201 return from full records (this is an estimate only)",
            "Have a registered tax practitioner review zero-rated, exempt and denied-input "
            "items before filing",
        ],
        notes=(
            f"At the standard rate of {VAT_RATE:.0%}: output VAT R{output_vat:,.2f} less "
            f"input VAT R{input_vat:,.2f} = net R{net:,.2f} ({position})."
        ),
        warnings=[
            "Simple estimate: assumes all sales standard-rated and all listed purchases "
            "carry claimable input VAT. Zero-rated exports, exempt supplies, apportionment "
            "and denied inputs are not modelled."
        ],
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "check-vat-registration-south-africa",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": (
            "VAT Act registration tests per SARS: compulsory above R2.3m taxable supplies "
            "in any consecutive 12 months, voluntary above R120,000 (both effective "
            "1 April 2026, Budget 2026); VAT rate 15% (2025 proposed increases reversed "
            "24 April 2025)"
        ),
        "tools_working": [
            "check_registration_required",
            "estimate_vat_position",
            "get_status",
        ],
        "tools_stubbed": [],
        "vat_rate": VAT_RATE,
        "mandatory_threshold_zar": MANDATORY_REGISTRATION_THRESHOLD_ZAR,
        "voluntary_minimum_zar": VOLUNTARY_REGISTRATION_MINIMUM_ZAR,
        "disclaimer": "Determination tool, not tax advice. Confirm with a registered tax practitioner.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
