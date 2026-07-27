"""
MIA Skill: Calculate South African PAYE for an employee's salary.

Computes monthly Pay-As-You-Earn (employees' tax) for the 2027 year of assessment
(1 March 2026 - 28 February 2027) using the annualisation method: annualise the
monthly remuneration, apply the 2027 individual tax table, subtract the age-based
rebates and (if applicable) the Medical Scheme Fees Tax Credit, then divide by 12.
Also computes the UIF employee contribution and the monthly take-home amount.

IMPORTANT context (current as of July 2026):
- The 2027 brackets, rebates, thresholds and medical credits all CHANGED from the
  2026 year - do not reuse 2026 constants. Everything below was re-verified against
  live SARS pages on 27 July 2026.
- Scope: a stable monthly cash salary. Bonuses, travel and other allowances, fringe
  benefits, retirement-fund deductions and variable remuneration all change the
  answer and are flagged requires_human. SDL (an employer levy) is out of scope.

Sources (all verified 27 July 2026):
- https://www.sars.gov.za/tax-rates/income-tax/rates-of-tax-for-individuals/
  (2027 brackets; primary/secondary/tertiary rebates R17,820 / R9,765 / R3,249;
  tax thresholds R99,000 / R153,250 / R171,300)
- https://www.sars.gov.za/tax-rates/medical-tax-credit-rates/
  (2027 Medical Scheme Fees Tax Credit: R376 pm taxpayer, R752 pm taxpayer + one
  dependant, R254 pm each additional dependant)
- https://www.sars.gov.za/types-of-tax/unemployment-insurance-fund/
  (UIF 1% employee + 1% employer; remuneration ceiling R17,712 per month /
  R212,544 annually with effect from 1 June 2021; max employee deduction R177.12)

This is a tool, not tax advice. Payroll edge cases belong with a payroll provider
or registered tax practitioner.

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.paye")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-paye-south-africa")

# --- Constants (SARS rules, 2027 year of assessment, verified 2026-07-27) --------

TAX_YEAR = 2027
TAX_YEAR_LABEL = "1 March 2026 - 28 February 2027"

# 2027 individual brackets. Tuple = (floor, base_tax, marginal_rate):
#   tax = base + rate * (taxable_income - floor) for the highest floor below income.
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

# 2027 rebates (same page, checked 2026-07-27). Cumulative by age:
# under 65: primary; 65-74: primary + secondary; 75+: primary + secondary + tertiary.
PRIMARY_REBATE = 17_820.0
SECONDARY_REBATE_65_PLUS = 9_765.0
TERTIARY_REBATE_75_PLUS = 3_249.0

# 2027 tax thresholds implied by the rebates (verified on the same page):
# under 65: R99,000 | 65-74: R153,250 | 75+: R171,300.
TAX_THRESHOLD_UNDER_65 = 99_000.0
TAX_THRESHOLD_65_TO_74 = 153_250.0
TAX_THRESHOLD_75_PLUS = 171_300.0

# 2027 Medical Scheme Fees Tax Credit, per month.
# Source: https://www.sars.gov.za/tax-rates/medical-tax-credit-rates/ (checked
# 2026-07-27): R376 for the taxpayer; R752 for the taxpayer and one dependant;
# R254 for each additional dependant.
MTC_FIRST_MEMBER_MONTHLY = 376.0
MTC_FIRST_TWO_MEMBERS_MONTHLY = 752.0
MTC_ADDITIONAL_MEMBER_MONTHLY = 254.0

# UIF: 1% employee contribution (employer adds a further 1%), on remuneration
# capped at R17,712 per month (R212,544 annually) with effect from 1 June 2021;
# maximum employee deduction R177.12 per month.
# Source: https://www.sars.gov.za/types-of-tax/unemployment-insurance-fund/
# (page last updated 15 Aug 2025; checked 2026-07-27).
UIF_RATE = 0.01
UIF_MONTHLY_REMUNERATION_CEILING = 17_712.0

# --- Models ---------------------------------------------------------------------


class PayeInput(BaseModel):
    """Inputs for the monthly PAYE calculation."""

    monthly_salary_zar: float = Field(
        ...,
        ge=0,
        description="Stable monthly cash salary (remuneration), in rand, before tax.",
    )
    age: int = Field(
        ...,
        ge=0,
        le=120,
        description="Employee's age in years (determines primary/secondary/tertiary rebates).",
    )
    medical_scheme_members: int = Field(
        default=0,
        ge=0,
        description="Number of people covered on the employee's medical scheme "
        "(the employee plus dependants). 0 = no medical scheme; enables the Medical "
        "Scheme Fees Tax Credit when > 0.",
    )


class PayeOutput(BaseModel):
    success: bool
    tax_year: int
    year_of_assessment: str
    monthly_salary_zar: float
    annual_remuneration_zar: float
    annual_tax_before_rebates_zar: float
    rebates_applied: list[str]
    total_rebates_zar: float
    medical_tax_credit_annual_zar: float
    annual_paye_zar: float
    monthly_paye_zar: float
    uif_employee_monthly_zar: float
    uif_employer_monthly_zar: float
    monthly_take_home_zar: float
    effective_paye_rate_on_salary: float
    below_tax_threshold: bool
    requires_human: bool = True
    human_steps: list[str] = []
    notes: str = ""
    warnings: list[str] = []


# --- Helpers --------------------------------------------------------------------


def _bracket_tax(amount: float, brackets: list[tuple[float, float, float]]) -> float:
    """Tax under a (floor, base, rate) marginal table."""
    tax = 0.0
    for floor, base, rate in brackets:
        if amount > floor:
            tax = base + rate * (amount - floor)
    return tax


def _rebates_for_age(age: int) -> tuple[float, list[str]]:
    """Cumulative age-based rebates for the 2027 year."""
    total = PRIMARY_REBATE
    applied = [f"primary R{PRIMARY_REBATE:,.0f}"]
    if age >= 65:
        total += SECONDARY_REBATE_65_PLUS
        applied.append(f"secondary (65+) R{SECONDARY_REBATE_65_PLUS:,.0f}")
    if age >= 75:
        total += TERTIARY_REBATE_75_PLUS
        applied.append(f"tertiary (75+) R{TERTIARY_REBATE_75_PLUS:,.0f}")
    return total, applied


def _mtc_monthly(members: int) -> float:
    """Medical Scheme Fees Tax Credit per month for the number of covered members."""
    if members <= 0:
        return 0.0
    if members == 1:
        return MTC_FIRST_MEMBER_MONTHLY
    return MTC_FIRST_TWO_MEMBERS_MONTHLY + MTC_ADDITIONAL_MEMBER_MONTHLY * (members - 2)


def _tax_threshold_for_age(age: int) -> float:
    if age >= 75:
        return TAX_THRESHOLD_75_PLUS
    if age >= 65:
        return TAX_THRESHOLD_65_TO_74
    return TAX_THRESHOLD_UNDER_65


def _uif_employee_monthly(monthly_salary: float) -> float:
    """UIF employee contribution: 1% of remuneration capped at the ceiling."""
    return round(UIF_RATE * min(monthly_salary, UIF_MONTHLY_REMUNERATION_CEILING), 2)


def _compute_paye(input: PayeInput) -> PayeOutput:
    """Shared computation for the monthly and annual tools."""
    annual = input.monthly_salary_zar * 12
    tax_before = _bracket_tax(annual, PERSONAL_TAX_BRACKETS_2027)
    rebates, rebates_applied = _rebates_for_age(input.age)
    mtc_annual = _mtc_monthly(input.medical_scheme_members) * 12

    annual_paye = max(0.0, tax_before - rebates - mtc_annual)
    monthly_paye = round(annual_paye / 12, 2)

    uif_employee = _uif_employee_monthly(input.monthly_salary_zar)
    take_home = round(input.monthly_salary_zar - monthly_paye - uif_employee, 2)

    threshold = _tax_threshold_for_age(input.age)
    below_threshold = annual <= threshold

    warnings = [
        "Annualisation method on a stable monthly salary: bonuses, allowances, fringe "
        "benefits, retirement-fund deductions and variable pay change the result. "
        "SARS's published employer deduction tables may also differ by a few rand due "
        "to income bucketing."
    ]
    if input.medical_scheme_members > 0:
        warnings.append(
            "Medical Scheme Fees Tax Credit assumes the employer processes it through "
            "payroll; additional medical expense credits (s6B) are not modelled."
        )

    return PayeOutput(
        success=True,
        tax_year=TAX_YEAR,
        year_of_assessment=TAX_YEAR_LABEL,
        monthly_salary_zar=round(input.monthly_salary_zar, 2),
        annual_remuneration_zar=round(annual, 2),
        annual_tax_before_rebates_zar=round(tax_before, 2),
        rebates_applied=rebates_applied,
        total_rebates_zar=round(rebates, 2),
        medical_tax_credit_annual_zar=round(mtc_annual, 2),
        annual_paye_zar=round(annual_paye, 2),
        monthly_paye_zar=monthly_paye,
        uif_employee_monthly_zar=uif_employee,
        uif_employer_monthly_zar=uif_employee,  # employer matches the 1% (2% total)
        monthly_take_home_zar=take_home,
        effective_paye_rate_on_salary=(
            round(monthly_paye / input.monthly_salary_zar, 4) if input.monthly_salary_zar else 0.0
        ),
        below_tax_threshold=below_threshold,
        requires_human=True,
        human_steps=[
            "Employer must be registered for PAYE with SARS; monthly employer "
            "declarations and payment deadlines apply",
            "UIF registration with the Department of Employment and Labour is a "
            "separate obligation from the SARS-collected contributions",
            "Confirm final payroll figures with a payroll provider or registered tax "
            "practitioner (bonuses, allowances, fringe benefits, retirement deductions)",
        ],
        notes=(
            f"2027 year of assessment ({TAX_YEAR_LABEL}). Monthly PAYE R{monthly_paye:,.2f} "
            f"on a salary of R{input.monthly_salary_zar:,.2f}; UIF employee contribution "
            f"R{uif_employee:,.2f} (employer adds the same again); take-home "
            f"R{take_home:,.2f}."
            + (
                f" Annual remuneration R{annual:,.0f} is at or below the R{threshold:,.0f} "
                "tax threshold for this age - no PAYE due."
                if below_threshold
                else ""
            )
        ),
        warnings=warnings,
    )


# --- Tools ----------------------------------------------------------------------


@mcp.tool()
async def calculate_monthly_paye(input: PayeInput) -> PayeOutput:
    """Calculate monthly PAYE, UIF employee contribution and take-home pay (2027 year).

    Annualisation method: annual tax on 12x the monthly salary via the 2027 table,
    less the age-based rebates (primary; secondary at 65+; tertiary at 75+), less
    the Medical Scheme Fees Tax Credit when medical_scheme_members > 0, divided
    by 12 and floored at zero. UIF employee contribution is 1% of remuneration
    capped at R17,712 per month (max R177.12).

    Limits:
    - Stable monthly cash salary only - bonuses, allowances, fringe benefits and
      retirement deductions are out of scope and flagged.
    - SDL (employer levy) not included; employer UIF shown for information.
    """
    logger.info(
        "calculate_monthly_paye: salary=%s age=%s members=%s",
        input.monthly_salary_zar,
        input.age,
        input.medical_scheme_members,
    )
    return _compute_paye(input)


@mcp.tool()
async def calculate_annual_summary(input: PayeInput) -> dict:
    """Annual view of the same calculation: total tax, total take-home, effective rate.

    Uses the identical 2027-year computation as calculate_monthly_paye and presents
    annual totals, including annual UIF and the effective tax rate on remuneration.
    """
    m = _compute_paye(input)
    annual_uif_employee = round(m.uif_employee_monthly_zar * 12, 2)
    annual_take_home = round(m.monthly_take_home_zar * 12, 2)
    return {
        "tax_year": m.tax_year,
        "year_of_assessment": m.year_of_assessment,
        "annual_remuneration_zar": m.annual_remuneration_zar,
        "annual_tax_before_rebates_zar": m.annual_tax_before_rebates_zar,
        "total_rebates_zar": m.total_rebates_zar,
        "medical_tax_credit_annual_zar": m.medical_tax_credit_annual_zar,
        "annual_paye_zar": m.annual_paye_zar,
        "annual_uif_employee_zar": annual_uif_employee,
        "annual_take_home_zar": annual_take_home,
        "effective_paye_rate_on_remuneration": m.effective_paye_rate_on_salary,
        "below_tax_threshold": m.below_tax_threshold,
        "requires_human": True,
        "notes": m.notes,
        "warnings": m.warnings,
    }


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status and the rule basis for this skill."""
    return {
        "skill": "calculate-paye-south-africa",
        "version": "0.1.0",
        "status": "alpha",
        "rule_basis": (
            "2027 individual tax table, rebates and thresholds; 2027 Medical Scheme "
            "Fees Tax Credit (R376/R752/R254 pm); UIF 1% employee + 1% employer, "
            "ceiling R17,712 pm (from 1 June 2021)"
        ),
        "tools_working": [
            "calculate_monthly_paye",
            "calculate_annual_summary",
            "get_status",
        ],
        "tools_stubbed": [],
        "tax_year_brackets": f"{TAX_YEAR} ({TAX_YEAR_LABEL})",
        "primary_rebate_zar": PRIMARY_REBATE,
        "uif_monthly_ceiling_zar": UIF_MONTHLY_REMUNERATION_CEILING,
        "disclaimer": "Calculation tool, not tax advice. Confirm payroll with a professional.",
        "last_rule_check": "2026-07",
    }


if __name__ == "__main__":
    mcp.run()
