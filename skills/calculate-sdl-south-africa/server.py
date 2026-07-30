"""
MIA Skill: Calculate the South African Skills Development Levy (SDL) and check liability.

SDL is a levy on employers, collected by SARS, of 1% of the leviable amount
(total salaries paid to employees, including wages, overtime payments, leave pay,
bonuses, fees, commissions and lump sum payments). Employers whose total
remuneration subject to SDL over the NEXT 12-month period won't exceed R500,000
are exempt, along with specific public-sector and exempt-organisation categories.

Together with calculate-paye-south-africa (PAYE + UIF), this completes the
employer's monthly SARS payroll cost picture.

This skill is PURE CALCULATION/DETERMINATION over published SARS rules. No
external systems, no credentials. Registration and payment are real SARS
processes and are always flagged requires_human.

Sources (verified 30 July 2026):
- https://www.sars.gov.za/types-of-tax/skills-development-levy/  (1% rate;
  R500,000 next-12-months exemption test; exempt employer categories; leviable
  amount components; page last updated 15 August 2025)

This is a tool, not tax advice. Confirm payroll obligations with a professional.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.sdl")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-sdl-south-africa")

# --- Constants (SARS rules, verified 2026-07-30) --------------------------------

# SDL rate: "1% of the total amount paid in salaries to employees (including
# wages, overtime payments, leave pay, bonuses, fees, commissions and lump sum
# payments)".
# Source: https://www.sars.gov.za/types-of-tax/skills-development-levy/
# (page last updated 15 Aug 2025; checked 2026-07-30).
SDL_RATE = 0.01

# Exemption: "Any employer whose total remuneration subject to SDL (leviable
# amount) paid/due to all its employees over the next 12 month period won't
# exceed R500 000" is exempt. Same source as above.
SDL_EXEMPTION_THRESHOLD_ZAR = 500_000.0

# Leviable amount components, per the same SARS page.
LEVIABLE_COMPONENTS = "wages, overtime payments, leave pay, bonuses, fees, commissions and lump sum payments"

# --- Models ---------------------------------------------------------------------


class SdlLiabilityInput(BaseModel):
    """Inputs for the SDL liability/exemption check."""

    expected_total_remuneration_next_12m_zar: float = Field(
        ...,
        ge=0,
        description="Total remuneration subject to SDL (leviable amount) expected to be "
        "paid to ALL employees over the NEXT 12 months, in rand.",
    )
    is_public_service_employer: bool = Field(
        default=False,
        description="National or provincial government (public service) employer.",
    )
    is_parliament_funded_public_entity: bool = Field(
        default=False,
        description="National/provincial public entity that is 80%+ funded by Parliament.",
    )
    is_pbo_with_exemption_letter: bool = Field(
        default=False,
        description="Public benefit organisation holding the SARS Tax Exemption Unit exemption letter.",
    )
    is_municipality_with_exemption_certificate: bool = Field(
        default=False,
        description="Municipality holding a ministerial exemption certificate.",
    )


class SdlLiabilityOutput(BaseModel):
    success: bool
    liable_for_sdl: bool
    exemption_reasons: list[str] = []
    exemption_threshold_zar: float
    expected_next_12m_remuneration_zar: float
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


class SdlCalculationInput(BaseModel):
    """Inputs for the monthly SDL calculation."""

    monthly_leviable_amount_zar: float = Field(
        ...,
        ge=0,
        description="Total leviable amount for the month: salaries including wages, "
        "overtime, leave pay, bonuses, fees, commissions and lump sums, in rand.",
    )


class SdlCalculationOutput(BaseModel):
    success: bool
    monthly_leviable_amount_zar: float
    sdl_rate: float
    monthly_sdl_zar: float
    annualised_leviable_amount_zar: float
    possibly_exempt: bool
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def check_sdl_liability(input: SdlLiabilityInput) -> SdlLiabilityOutput:
    """Check whether an employer is liable for the Skills Development Levy.

    Applies the SARS exemption tests:
    - Expected total remuneration subject to SDL over the next 12 months at or
      below R500,000 -> exempt.
    - Public service employers, 80%+ Parliament-funded public entities, PBOs with
      a Tax Exemption Unit letter, and municipalities with a ministerial
      exemption certificate -> exempt.

    Limits: the forward-looking R500,000 test is an estimate by nature - if the
    business is near the line or growing, get practitioner advice; liability can
    arise mid-year when the expectation changes.
    """
    logger.info("check_sdl_liability: expected_12m=%s", input.expected_total_remuneration_next_12m_zar)

    reasons: list[str] = []
    warnings: list[str] = []

    if input.expected_total_remuneration_next_12m_zar <= SDL_EXEMPTION_THRESHOLD_ZAR:
        reasons.append(
            f"Expected leviable remuneration over the next 12 months "
            f"(R{input.expected_total_remuneration_next_12m_zar:,.0f}) does not exceed "
            f"R{SDL_EXEMPTION_THRESHOLD_ZAR:,.0f}."
        )
    if input.is_public_service_employer:
        reasons.append("Public service employer (national/provincial government).")
    if input.is_parliament_funded_public_entity:
        reasons.append("National/provincial public entity 80%+ funded by Parliament.")
    if input.is_pbo_with_exemption_letter:
        reasons.append("Public benefit organisation with a Tax Exemption Unit letter.")
    if input.is_municipality_with_exemption_certificate:
        reasons.append("Municipality holding a ministerial exemption certificate.")

    liable = len(reasons) == 0

    near_line = (
        SDL_EXEMPTION_THRESHOLD_ZAR
        < input.expected_total_remuneration_next_12m_zar
        <= SDL_EXEMPTION_THRESHOLD_ZAR * 1.2
    )
    if near_line:
        warnings.append(
            "Expected remuneration is within 20% of the R500,000 exemption line - the "
            "test is forward-looking, so document the estimate and revisit it if "
            "headcount or pay changes."
        )

    return SdlLiabilityOutput(
        success=True,
        liable_for_sdl=liable,
        exemption_reasons=reasons,
        exemption_threshold_zar=SDL_EXEMPTION_THRESHOLD_ZAR,
        expected_next_12m_remuneration_zar=round(input.expected_total_remuneration_next_12m_zar, 2),
        requires_human=True,
        human_steps=[
            "If liable: register for SDL with SARS (handled through the employer "
            "registration processes alongside PAYE) and include SDL in the monthly "
            "employer declaration and payment",
            "Confirm the forward-looking R500,000 estimate with a payroll provider or "
            "practitioner, and revisit it when pay or headcount changes",
        ],
        notes=(
            "Liable: SDL of 1% of the leviable amount applies."
            if liable
            else "Exempt on the rules checked here: " + " ".join(reasons)
        ),
        warnings=warnings,
    )


@mcp.tool()
async def calculate_sdl(input: SdlCalculationInput) -> SdlCalculationOutput:
    """Calculate the monthly Skills Development Levy at 1% of the leviable amount.

    The leviable amount is total salaries including wages, overtime payments,
    leave pay, bonuses, fees, commissions and lump sum payments. If the
    annualised amount is at or below R500,000 the employer may be exempt
    entirely - the output flags this and points to check_sdl_liability.
    """
    logger.info("calculate_sdl: monthly=%s", input.monthly_leviable_amount_zar)

    sdl = round(input.monthly_leviable_amount_zar * SDL_RATE, 2)
    annualised = input.monthly_leviable_amount_zar * 12
    possibly_exempt = annualised <= SDL_EXEMPTION_THRESHOLD_ZAR

    warnings: list[str] = []
    if possibly_exempt and input.monthly_leviable_amount_zar > 0:
        warnings.append(
            f"Annualised leviable amount (R{annualised:,.0f}) is at or below the "
            f"R{SDL_EXEMPTION_THRESHOLD_ZAR:,.0f} exemption threshold - this employer "
            "may not owe SDL at all. Run check_sdl_liability."
        )

    return SdlCalculationOutput(
        success=True,
        monthly_leviable_amount_zar=round(input.monthly_leviable_amount_zar, 2),
        sdl_rate=SDL_RATE,
        monthly_sdl_zar=sdl,
        annualised_leviable_amount_zar=round(annualised, 2),
        possibly_exempt=possibly_exempt,
        requires_human=True,
        human_steps=[
            "Include SDL in the monthly employer declaration and payment to SARS",
            "Confirm which pay items fall into the leviable amount for this payroll "
            f"({LEVIABLE_COMPONENTS}) with a payroll provider",
        ],
        notes=(
            f"SDL at {SDL_RATE:.0%} of R{input.monthly_leviable_amount_zar:,.2f} = "
            f"R{sdl:,.2f} for the month. SDL is an EMPLOYER cost - it is not deducted "
            "from employees."
        ),
        warnings=warnings,
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-sdl-south-africa",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": (
            "Skills Development Levies Act as administered by SARS: 1% of the leviable "
            "amount; R500,000 next-12-months exemption threshold; public-sector and "
            "exempt-organisation categories"
        ),
        "tools_working": ["check_sdl_liability", "calculate_sdl", "get_status"],
        "tools_stubbed": [],
        "sdl_rate": SDL_RATE,
        "exemption_threshold_zar": SDL_EXEMPTION_THRESHOLD_ZAR,
        "disclaimer": "Calculation tool, not tax advice. Confirm payroll with a professional.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
