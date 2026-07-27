"""Tests for the calculate-paye-south-africa MCP server.

These tests pin the real SARS 2027-year rules so we catch any drift.
Verified on SARS 2026-07-27:
    Brackets: 18% to R245,100 | 44,118 + 26% | 79,998 + 31% | 125,599 + 36% |
    185,215 + 39% | 259,783 + 41% | 666,339 + 45% above R1,878,600.
    Rebates: primary R17,820; secondary (65+) R9,765; tertiary (75+) R3,249.
    Thresholds: R99,000 / R153,250 / R171,300.
    MTC per month: R376 (1 member), R752 (2), +R254 each additional.
    UIF: 1% employee, ceiling R17,712 pm -> max R177.12.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    PayeInput,
    calculate_annual_summary,
    calculate_monthly_paye,
    get_status,
)

# --- Core PAYE: brackets and rebates ---------------------------------------------


class TestMonthlyPaye:
    async def test_zero_salary_all_zero(self):
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=0, age=30))
        assert out.success is True
        assert out.monthly_paye_zar == 0.0
        assert out.uif_employee_monthly_zar == 0.0
        assert out.monthly_take_home_zar == 0.0

    async def test_below_threshold_no_paye_but_uif_still_due(self):
        """R8,000 pm = R96,000 pa, under the R99,000 threshold: PAYE 0, UIF 1%."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=8_000, age=30))
        assert out.below_tax_threshold is True
        assert out.monthly_paye_zar == 0.0
        assert out.uif_employee_monthly_zar == 80.0
        assert out.monthly_take_home_zar == 7_920.0

    async def test_exactly_at_threshold_zero_paye(self):
        """R8,250 pm = R99,000 pa: tax 17,820 minus primary rebate 17,820 = 0."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=8_250, age=64))
        assert out.annual_tax_before_rebates_zar == 17_820.0
        assert out.monthly_paye_zar == 0.0

    async def test_reference_case_30k_under_65(self):
        """R30,000 pm = R360,000 pa -> 44,118 + 26% of 114,900 = 73,992;
        less primary 17,820 -> 56,172 pa -> R4,681.00 pm. UIF capped at R177.12."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=30_000, age=40))
        assert out.annual_tax_before_rebates_zar == 73_992.0
        assert out.annual_paye_zar == 56_172.0
        assert out.monthly_paye_zar == 4_681.0
        assert out.uif_employee_monthly_zar == 177.12
        assert out.monthly_take_home_zar == 25_141.88

    async def test_top_bracket_45_percent(self):
        """R200,000 pm = R2.4m pa -> 666,339 + 45% of 521,400 = 900,969;
        less primary -> 883,149 pa -> R73,595.75 pm."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=200_000, age=45))
        assert out.annual_tax_before_rebates_zar == 900_969.0
        assert out.monthly_paye_zar == 73_595.75

    def test_negative_salary_rejected(self):
        with pytest.raises(ValidationError):
            PayeInput(monthly_salary_zar=-1, age=30)

    def test_absurd_age_rejected(self):
        with pytest.raises(ValidationError):
            PayeInput(monthly_salary_zar=10_000, age=150)


class TestAgeBasedRebates:
    async def test_age_65_gets_secondary_rebate(self):
        """Same R30,000 salary at 65: PAYE drops by 9,765/12 vs the under-65 case."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=30_000, age=65))
        assert len(out.rebates_applied) == 2
        assert out.total_rebates_zar == 27_585.0  # 17,820 + 9,765
        assert out.annual_paye_zar == 46_407.0  # 73,992 - 27,585
        assert out.monthly_paye_zar == 3_867.25

    async def test_age_64_still_only_primary(self):
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=30_000, age=64))
        assert len(out.rebates_applied) == 1
        assert out.monthly_paye_zar == 4_681.0

    async def test_age_75_gets_all_three_rebates(self):
        """At 75: rebates total 30,834 -> annual PAYE 43,158 -> R3,596.50 pm."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=30_000, age=75))
        assert len(out.rebates_applied) == 3
        assert out.total_rebates_zar == 30_834.0  # 17,820 + 9,765 + 3,249
        assert out.monthly_paye_zar == 3_596.5

    async def test_pensioner_below_65plus_threshold(self):
        """R12,770 pm = R153,240 pa, under the 65+ threshold of R153,250 -> PAYE 0
        (the same salary under 65 WOULD pay tax)."""
        senior = await calculate_monthly_paye(PayeInput(monthly_salary_zar=12_770, age=68))
        junior = await calculate_monthly_paye(PayeInput(monthly_salary_zar=12_770, age=40))
        assert senior.below_tax_threshold is True
        assert senior.monthly_paye_zar == 0.0
        assert junior.monthly_paye_zar > 0.0


class TestMedicalTaxCredit:
    async def test_single_member_credit(self):
        """R30,000 pm, 1 member: MTC 376 x 12 = 4,512 pa ->
        56,172 - 4,512 = 51,660 pa -> R4,305.00 pm."""
        out = await calculate_monthly_paye(
            PayeInput(monthly_salary_zar=30_000, age=40, medical_scheme_members=1)
        )
        assert out.medical_tax_credit_annual_zar == 4_512.0
        assert out.monthly_paye_zar == 4_305.0

    async def test_family_of_three_credit(self):
        """3 members: (752 + 254) x 12 = 12,072 pa -> 44,100 pa -> R3,675.00 pm."""
        out = await calculate_monthly_paye(
            PayeInput(monthly_salary_zar=30_000, age=40, medical_scheme_members=3)
        )
        assert out.medical_tax_credit_annual_zar == 12_072.0
        assert out.monthly_paye_zar == 3_675.0

    async def test_credit_cannot_push_paye_negative(self):
        """Low salary + large family: PAYE floors at zero, no negative tax."""
        out = await calculate_monthly_paye(
            PayeInput(monthly_salary_zar=9_000, age=40, medical_scheme_members=6)
        )
        assert out.monthly_paye_zar == 0.0


class TestUif:
    async def test_uif_below_ceiling_is_1_percent(self):
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=10_000, age=30))
        assert out.uif_employee_monthly_zar == 100.0
        assert out.uif_employer_monthly_zar == 100.0

    async def test_uif_at_ceiling_exact(self):
        """R17,712 pm is the ceiling: contribution exactly R177.12."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=17_712, age=30))
        assert out.uif_employee_monthly_zar == 177.12

    async def test_uif_capped_above_ceiling(self):
        """Salary above the ceiling still contributes only R177.12."""
        out = await calculate_monthly_paye(PayeInput(monthly_salary_zar=50_000, age=30))
        assert out.uif_employee_monthly_zar == 177.12


# --- Annual summary --------------------------------------------------------------


class TestAnnualSummary:
    async def test_annual_matches_monthly_times_twelve(self):
        monthly = await calculate_monthly_paye(PayeInput(monthly_salary_zar=30_000, age=40))
        annual = await calculate_annual_summary(PayeInput(monthly_salary_zar=30_000, age=40))
        assert annual["annual_paye_zar"] == monthly.annual_paye_zar
        assert annual["annual_uif_employee_zar"] == round(monthly.uif_employee_monthly_zar * 12, 2)
        assert annual["annual_take_home_zar"] == round(monthly.monthly_take_home_zar * 12, 2)

    async def test_effective_rate_reported(self):
        annual = await calculate_annual_summary(PayeInput(monthly_salary_zar=30_000, age=40))
        # 4,681 / 30,000 = 15.60%
        assert annual["effective_paye_rate_on_remuneration"] == pytest.approx(0.156, abs=0.001)


# --- Status / structural ---------------------------------------------------------


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-paye-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert s["primary_rebate_zar"] == 17_820.0
        assert s["uif_monthly_ceiling_zar"] == 17_712.0


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-paye-south-africa"
