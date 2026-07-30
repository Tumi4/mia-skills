"""
MIA Skill: Calculate the South African Section 12B solar / renewable energy tax deduction.

Section 12B of the Income Tax Act (No. 58 of 1962) allows a business taxpayer to deduct
the cost of qualifying renewable-energy generation assets from taxable income. For solar
PV, this is a 100% deduction in the year the asset is brought into use (no 1 MW cap for PV).

This skill is PURE CALCULATION over published SARS rules. No external systems, no browser
automation, no credentials. It is deterministic and fully testable.

IMPORTANT context (current as of 2026):
- Section 12B (100% year-one PV deduction) is PERMANENT and still in force.
- Section 12BA (the enhanced 125% allowance) EXPIRED on 28 February 2025 and was NOT renewed.
  Assets brought into use after that date do NOT qualify for the 125% rate.
- This skill calculates the live Section 12B benefit, and can also show what the lapsed
  12BA benefit *would* have been, for educational comparison, clearly flagged as expired.

Personal income tax figures are the 2027 year of assessment (1 March 2026 - 28 February 2027).

This is a tool, not tax advice. Always have a registered tax practitioner confirm any claim.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging
from datetime import date
from enum import StrEnum

from fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("mia.section-12b")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-section-12b-solar-deduction")

# ─── Constants (SARS rules, current 2027 year of assessment) ────────────────────

# Section 12B: 100% year-one deduction for qualifying PV solar (no cap for PV).
SECTION_12B_RATE = 1.00

# Section 12BA: enhanced 125% — EXPIRED 28 Feb 2025. Retained for educational comparison.
SECTION_12BA_RATE = 1.25
SECTION_12BA_EXPIRY = date(2025, 2, 28)

# Corporate income tax rate (companies), current.
CORPORATE_TAX_RATE = 0.27

# Ordinary trusts (other than special trusts) are taxed at a flat rate, current.
# Source: SARS "Companies, Trusts and SBC" rate table (45% for years of assessment
# from 1 March 2023 onwards). Special trusts are taxed on the individual brackets.
TRUST_FLAT_RATE = 0.45

# 2027 SARS personal income tax brackets (year of assessment 1 March 2026 - 28 February 2027).
# Source: https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/
# Checked against the live SARS table on 2026-07-30.
# (lower_bound_inclusive, upper_bound_inclusive_or_None, base_tax, marginal_rate)
PERSONAL_TAX_BRACKETS_2027 = [
    (0, 245_100, 0, 0.18),
    (245_101, 383_100, 44_118, 0.26),
    (383_101, 530_200, 79_998, 0.31),
    (530_201, 695_800, 125_599, 0.36),
    (695_801, 887_000, 185_215, 0.39),
    (887_001, 1_878_600, 259_783, 0.41),
    (1_878_601, None, 666_339, 0.45),
]


class TaxpayerType(StrEnum):
    company = "company"  # flat 27%
    individual = "individual"  # progressive individual brackets
    sole_proprietor = "sole_proprietor"  # taxed at individual rates
    trust = "trust"  # ORDINARY trust: flat 45% (not the individual brackets)
    special_trust = "special_trust"  # taxed at individual rates (e.g. disability/minor trusts)


# ─── Models ────────────────────────────────────────────────────────────────────


class DeductionInput(BaseModel):
    """Inputs to calculate a Section 12B solar deduction."""

    equipment_cost_zar: float = Field(
        ...,
        gt=0,
        description="Cost of QUALIFYING equipment only (panels, inverters, mounting, batteries "
        "integrated with PV). EXCLUDE installation labour — SARS does not allow 12B on labour.",
    )
    installation_labour_zar: float = Field(
        default=0,
        ge=0,
        description="Installation labour cost (does NOT qualify for 12B; captured for the "
        "founder's total project cost picture only).",
    )
    taxpayer_type: TaxpayerType = Field(default=TaxpayerType.company)
    taxable_income_zar: float = Field(
        ...,
        gt=0,
        description="The taxpayer's taxable income for the year BEFORE this deduction. "
        "Needed to compute the real cash tax saving.",
    )
    brought_into_use_date: date = Field(
        default_factory=date.today,
        description="Date the system was commissioned and producing electricity (per the CoC).",
    )
    grant_funded_portion_zar: float = Field(
        default=0,
        ge=0,
        description="Portion of equipment cost funded by a government grant. 12B applies only "
        "to the taxpayer's own-funded portion.",
    )

    @field_validator("installation_labour_zar")
    @classmethod
    def labour_not_negative(cls, v: float) -> float:
        return v


class DeductionOutput(BaseModel):
    success: bool
    qualifying_cost_zar: float
    deduction_zar: float
    section_applied: str
    marginal_rate_used: float
    cash_tax_saving_zar: float
    effective_net_cost_zar: float
    total_project_cost_zar: float
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


# ─── Tax helpers ────────────────────────────────────────────────────────────────


def _marginal_rate_for_individual(taxable_income: float) -> float:
    """Return the marginal tax rate for an individual at a given taxable income (2027)."""
    for _lower, upper, _base, rate in PERSONAL_TAX_BRACKETS_2027:
        if upper is None or taxable_income <= upper:
            return rate
    return PERSONAL_TAX_BRACKETS_2027[-1][3]


def _personal_tax(taxable_income: float) -> float:
    """Compute total personal income tax for a given taxable income (2027 brackets).

    NOTE: this deliberately excludes the primary rebate (R17,820 for 2027). It is only
    ever used as a *difference* (tax_before - tax_after), where the constant rebate
    cancels, so the cash-saving figure stays correct. Do not "fix" by adding the rebate
    unless you also change every call site to use absolute tax payable.
    """
    for lower, upper, base, rate in PERSONAL_TAX_BRACKETS_2027:
        if upper is None or taxable_income <= upper:
            return base + (taxable_income - (lower - 1 if lower > 0 else 0)) * rate
    return 0.0


# Taxpayers on the progressive individual brackets vs flat-rate taxpayers.
_PROGRESSIVE_TYPES = (
    TaxpayerType.individual,
    TaxpayerType.sole_proprietor,
    TaxpayerType.special_trust,
)
_FLAT_RATES = {
    TaxpayerType.company: CORPORATE_TAX_RATE,
    TaxpayerType.trust: TRUST_FLAT_RATE,
}


def _cash_tax_saving(
    deduction: float, taxpayer_type: TaxpayerType, taxable_income: float
) -> tuple[float, float, bool]:
    """Compute the real cash tax saving from a deduction, by taxpayer type.

    Returns (rate_used, cash_saving, exceeds_income).

    - Flat-rate taxpayers (company 27%, ordinary trust 45%): saving = rate x absorbed,
      where absorbed is capped at taxable income. Any excess becomes an assessed loss
      carried forward (exceeds_income is True), not an immediate cash saving.
    - Progressive taxpayers (individual, sole proprietor, special trust): saving is the
      difference in tax on the individual brackets, tax(income) - tax(income - deduction).
    """
    if taxpayer_type in _PROGRESSIVE_TYPES:
        rate = _marginal_rate_for_individual(taxable_income)
        saving = _personal_tax(taxable_income) - _personal_tax(max(0.0, taxable_income - deduction))
        return rate, saving, False
    rate = _FLAT_RATES[taxpayer_type]
    absorbed = min(deduction, taxable_income)
    return rate, absorbed * rate, deduction > taxable_income


# ─── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def calculate_deduction(input: DeductionInput) -> DeductionOutput:
    """Calculate the Section 12B solar/renewable-energy tax deduction and real cash saving.

    Section 12B gives a 100% year-one deduction on qualifying renewable energy equipment
    (for solar PV, with no capacity cap). This tool computes:
      - the qualifying cost (own-funded equipment, excluding labour and grant portions)
      - the deduction amount
      - the real cash tax saving, using the correct rate for the taxpayer type
      - the effective net cost of the system after the tax benefit

    Limits and notes:
    - Labour does not qualify for 12B and is excluded from the deduction (but shown in total cost).
    - Grant-funded portions do not qualify; only own-funded equipment counts.
    - Section 12BA (125%) expired 28 Feb 2025; this tool applies the live 12B 100% rate.
    - A valid Certificate of Compliance (CoC) from a registered electrician is required by SARS.
    """
    logger.info("calculate_deduction: cost=%s type=%s", input.equipment_cost_zar, input.taxpayer_type)

    warnings: list[str] = []

    # Qualifying cost = own-funded equipment only (exclude grant portion, exclude labour)
    own_funded_equipment = max(0.0, input.equipment_cost_zar - input.grant_funded_portion_zar)
    qualifying_cost = own_funded_equipment

    if input.grant_funded_portion_zar > 0:
        warnings.append(
            f"R{input.grant_funded_portion_zar:,.0f} grant-funded portion excluded — "
            "12B applies only to own-funded expenditure."
        )

    # Determine which section applies based on brought-into-use date
    if input.brought_into_use_date <= SECTION_12BA_EXPIRY:
        # Historically could have used 12BA (125%); but default to 12B unless explicitly modelling 12BA
        section_applied = "Section 12B (100%)"
        rate = SECTION_12B_RATE
        warnings.append(
            "Asset brought into use before 28 Feb 2025 — the enhanced 125% Section 12BA "
            "may have applied. Use compare_12b_vs_12ba to see the difference."
        )
    else:
        section_applied = "Section 12B (100%)"
        rate = SECTION_12B_RATE

    deduction = qualifying_cost * rate

    # Real cash tax saving depends on taxpayer type (see _cash_tax_saving).
    marginal_rate, cash_saving, exceeds_income = _cash_tax_saving(
        deduction, input.taxpayer_type, input.taxable_income_zar
    )
    if exceeds_income:
        warnings.append(
            "Deduction exceeds taxable income — excess creates/increases an assessed loss "
            "carried forward, not an immediate cash saving."
        )

    total_project_cost = input.equipment_cost_zar + input.installation_labour_zar
    effective_net_cost = total_project_cost - cash_saving

    return DeductionOutput(
        success=True,
        qualifying_cost_zar=round(qualifying_cost, 2),
        deduction_zar=round(deduction, 2),
        section_applied=section_applied,
        marginal_rate_used=marginal_rate,
        cash_tax_saving_zar=round(cash_saving, 2),
        effective_net_cost_zar=round(effective_net_cost, 2),
        total_project_cost_zar=round(total_project_cost, 2),
        requires_human=True,
        human_steps=[
            "Obtain a valid Certificate of Compliance (CoC) from a registered electrician",
            "Ensure equipment is itemised separately from labour on the invoice",
            "Confirm the commissioning date falls in the intended tax year",
            "Have a registered tax practitioner confirm the claim before filing",
        ],
        notes=(
            f"{section_applied} applied at {rate:.0%}. "
            f"Effective net cost after tax benefit: R{effective_net_cost:,.0f} "
            f"on a total project of R{total_project_cost:,.0f}."
        ),
        warnings=warnings,
    )


@mcp.tool()
async def compare_12b_vs_12ba(
    equipment_cost_zar: float,
    taxpayer_type: TaxpayerType = TaxpayerType.company,
    taxable_income_zar: float = 1_000_000,
) -> dict:
    """Compare the live Section 12B (100%) benefit against the expired Section 12BA (125%).

    Educational: shows founders exactly what the lapse of 12BA cost them, and confirms
    12B is still a strong incentive on its own.
    """
    deduction_12b = equipment_cost_zar * SECTION_12B_RATE
    deduction_12ba = equipment_cost_zar * SECTION_12BA_RATE

    _, saving_12b, _ = _cash_tax_saving(deduction_12b, taxpayer_type, taxable_income_zar)
    _, saving_12ba, _ = _cash_tax_saving(deduction_12ba, taxpayer_type, taxable_income_zar)

    return {
        "equipment_cost_zar": equipment_cost_zar,
        "section_12b_live": {
            "rate": "100%",
            "deduction_zar": round(deduction_12b, 2),
            "cash_saving_zar": round(saving_12b, 2),
            "status": "ACTIVE — permanent legislation, no expiry",
        },
        "section_12ba_expired": {
            "rate": "125%",
            "deduction_zar": round(deduction_12ba, 2),
            "cash_saving_zar": round(saving_12ba, 2),
            "status": "EXPIRED 28 Feb 2025 — not available for new installations",
        },
        "benefit_lost_to_expiry_zar": round(saving_12ba - saving_12b, 2),
        "takeaway": (
            "Section 12B alone still delivers a 100% year-one deduction on qualifying solar PV. "
            "The expiry of 12BA removed roughly a 7% incremental benefit on equipment cost, "
            "but 12B remains strong enough to make commercial solar financially compelling."
        ),
    }


@mcp.tool()
async def check_eligibility(
    is_business_use: bool,
    owns_asset: bool,
    has_certificate_of_compliance: bool,
    is_new_and_unused: bool,
    asset_type: str = "solar_pv",
) -> dict:
    """Check whether a renewable energy asset qualifies for the Section 12B deduction.

    Walks the core SARS eligibility conditions and returns a clear pass/fail with reasons.
    """
    blockers = []
    if not is_business_use:
        blockers.append(
            "Asset must be used in the production of income (a trade). Residential/personal "
            "use does not qualify under 12B. (Note: the individual solar rebate s6C ended after 2024.)"
        )
    if not owns_asset:
        blockers.append(
            "Taxpayer must own the asset (or acquire it under an instalment credit agreement). "
            "Operating-lease equipment is claimed by the lessor, not the user."
        )
    if not has_certificate_of_compliance:
        blockers.append(
            "A valid Certificate of Compliance (CoC) from a registered electrician is required. "
            "Without it, SARS will reject the claim."
        )
    if not is_new_and_unused:
        blockers.append("Asset must be new and unused, brought into use for the first time by the taxpayer.")

    fossil = asset_type.lower() in ("diesel", "generator", "gas", "petrol")
    if fossil:
        blockers.append(
            f"'{asset_type}' is a fossil-fuel asset and does not qualify. Only renewable sources "
            "(solar PV, wind, hydro, concentrated solar, biomass) qualify under 12B."
        )

    eligible = len(blockers) == 0
    return {
        "eligible": eligible,
        "asset_type": asset_type,
        "blockers": blockers,
        "next_step": (
            "You appear to qualify. Use calculate_deduction to compute your benefit."
            if eligible
            else "Resolve the blockers above, then re-check. Consult a tax practitioner if unsure."
        ),
    }


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-section-12b-solar-deduction",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": "SARS Income Tax Act s12B (live), s12BA (expired 28 Feb 2025)",
        "tools_working": [
            "calculate_deduction",
            "compare_12b_vs_12ba",
            "check_eligibility",
            "get_status",
        ],
        "tools_stubbed": [],
        "tax_year_brackets": "2027 (1 March 2026 - 28 February 2027)",
        "corporate_rate": CORPORATE_TAX_RATE,
        "disclaimer": "Calculation tool, not tax advice. Confirm with a registered tax practitioner.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
