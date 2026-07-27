"""Tests for the calculate-turnover-tax-south-africa MCP server.

These tests pin the real SARS rules so we catch any drift if the constants change.
2027 table (1 Mar 2026 - 28 Feb 2027, verified on SARS 2026-07-27):
    R0-600,000: 0% | R600,001-950,000: 1% above 600k
    R950,001-1,400,000: R3,500 + 2% above 950k | R1,400,001+: R12,500 + 3% above 1.4m
Qualifying limit: R2.3m (Budget 2026; previously R1m).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    CompareInput,
    EligibilityInput,
    EntityType,
    TurnoverTaxInput,
    calculate_turnover_tax,
    check_eligibility,
    compare_vs_standard_tax,
    get_status,
)

# --- Core calculation: 2027 table ------------------------------------------------


class TestCalculateTurnoverTax2027:
    async def test_zero_turnover_zero_tax(self):
        """A micro business with no receipts owes nothing (and input 0 is valid)."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=0))
        assert out.success is True
        assert out.turnover_tax_zar == 0.0
        assert out.effective_rate == 0.0

    async def test_tax_free_band_upper_boundary(self):
        """R600,000 exactly is still in the 0% band (2027)."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=600_000))
        assert out.turnover_tax_zar == 0.0
        assert "tax-free" in out.band_applied

    async def test_first_rand_above_tax_free_band(self):
        """R600,001 pays 1% of R1 = one cent."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=600_001))
        assert out.turnover_tax_zar == 0.01

    async def test_mid_first_band_800k(self):
        """R800,000 -> 1% of R200,000 = R2,000."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=800_000))
        assert out.turnover_tax_zar == 2_000.0

    async def test_band_boundary_950k_is_continuous(self):
        """R950,000 -> 1% of R350,000 = R3,500, which equals the next band's base.

        This pins the resolution of the SARS wording discrepancy: the rates-page
        formula ("2% above 950 000") is the one consistent with a R3,500 base.
        """
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=950_000))
        assert out.turnover_tax_zar == 3_500.0

    async def test_mid_second_band_1_2m(self):
        """R1.2m -> R3,500 + 2% of R250,000 = R8,500."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=1_200_000))
        assert out.turnover_tax_zar == 8_500.0

    async def test_band_boundary_1_4m_is_continuous(self):
        """R1.4m -> R3,500 + 2% of R450,000 = R12,500 = the top band's base."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=1_400_000))
        assert out.turnover_tax_zar == 12_500.0

    async def test_top_of_qualifying_range_2_3m(self):
        """R2.3m (the new limit) -> R12,500 + 3% of R900,000 = R39,500, no warning."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=2_300_000))
        assert out.turnover_tax_zar == 39_500.0
        assert out.exceeds_qualifying_limit is False
        assert out.warnings == []

    async def test_above_qualifying_limit_warns(self):
        """R2.5m exceeds the R2.3m limit: computed figure + explicit warning."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=2_500_000))
        assert out.turnover_tax_zar == 45_500.0  # 12,500 + 3% of 1.1m
        assert out.exceeds_qualifying_limit is True
        assert any("does not qualify" in w for w in out.warnings)

    async def test_requires_human_always_true(self):
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=700_000))
        assert out.requires_human is True
        assert any("practitioner" in s for s in out.human_steps)

    def test_negative_turnover_rejected(self):
        with pytest.raises(ValidationError):
            TurnoverTaxInput(annual_turnover_zar=-1)


class TestCalculateTurnoverTax2026:
    """The pre-Budget 2026 table is retained for prior-year work."""

    async def test_2026_tax_free_band(self):
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=335_000, tax_year=2026))
        assert out.turnover_tax_zar == 0.0

    async def test_2026_band_boundary_750k(self):
        """R750,000 -> R1,650 + 2% of R250,000 = R6,650 (2026 table)."""
        out = await calculate_turnover_tax(TurnoverTaxInput(annual_turnover_zar=750_000, tax_year=2026))
        assert out.turnover_tax_zar == 6_650.0

    async def test_2026_old_limit_was_1m(self):
        """R1m was the old qualifying limit: fine in 2026, over in 2027 it is not."""
        out_2026 = await calculate_turnover_tax(
            TurnoverTaxInput(annual_turnover_zar=1_000_000, tax_year=2026)
        )
        assert out_2026.exceeds_qualifying_limit is False
        assert out_2026.turnover_tax_zar == 14_150.0  # 6,650 + 3% of 250k
        out_2027 = await calculate_turnover_tax(
            TurnoverTaxInput(annual_turnover_zar=1_000_000, tax_year=2027)
        )
        assert out_2027.exceeds_qualifying_limit is False  # under the new R2.3m limit
        assert out_2027.turnover_tax_zar == 4_500.0  # 3,500 + 2% of 50k


# --- Eligibility -----------------------------------------------------------------


class TestEligibility:
    async def test_clean_micro_business_qualifies(self):
        result = await check_eligibility(
            EligibilityInput(annual_turnover_zar=900_000, entity_type=EntityType.sole_proprietor)
        )
        assert result["eligible_on_checked_rules"] is True
        assert result["blockers"] == []

    async def test_over_limit_blocked(self):
        result = await check_eligibility(EligibilityInput(annual_turnover_zar=2_400_000))
        assert result["eligible_on_checked_rules"] is False
        assert any("2,300,000" in b for b in result["blockers"])

    async def test_professional_services_over_20_percent_blocked(self):
        result = await check_eligibility(
            EligibilityInput(annual_turnover_zar=500_000, professional_service_receipts_percent=25)
        )
        assert result["eligible_on_checked_rules"] is False
        assert any("professional service" in b for b in result["blockers"])

    async def test_professional_services_at_exactly_20_percent_allowed(self):
        """The SARS FAQ says MORE than 20% disqualifies - exactly 20% passes."""
        result = await check_eligibility(
            EligibilityInput(annual_turnover_zar=500_000, professional_service_receipts_percent=20)
        )
        assert result["eligible_on_checked_rules"] is True

    async def test_personal_service_provider_blocked(self):
        result = await check_eligibility(
            EligibilityInput(
                annual_turnover_zar=500_000,
                is_personal_service_provider_or_labour_broker=True,
            )
        )
        assert result["eligible_on_checked_rules"] is False

    async def test_unlisted_shares_blocked(self):
        result = await check_eligibility(
            EligibilityInput(annual_turnover_zar=500_000, holds_shares_in_unlisted_companies=True)
        )
        assert result["eligible_on_checked_rules"] is False
        assert any("unlisted" in b for b in result["blockers"])

    async def test_company_needs_feb_year_end_and_natural_shareholders(self):
        result = await check_eligibility(
            EligibilityInput(
                annual_turnover_zar=500_000,
                entity_type=EntityType.company,
                company_year_end_february=False,
                all_shareholders_natural_persons=False,
            )
        )
        assert result["eligible_on_checked_rules"] is False
        assert len(result["blockers"]) == 2

    async def test_year_end_rule_ignored_for_sole_proprietor(self):
        """The February year-end rule is a company rule, not a sole-prop rule."""
        result = await check_eligibility(
            EligibilityInput(
                annual_turnover_zar=500_000,
                entity_type=EntityType.sole_proprietor,
                company_year_end_february=False,
            )
        )
        assert result["eligible_on_checked_rules"] is True

    async def test_unchecked_rules_are_disclosed(self):
        """Honesty pin: the tool must disclose the Sixth Schedule rules it does NOT check."""
        result = await check_eligibility(EligibilityInput(annual_turnover_zar=500_000))
        assert len(result["not_checked"]) > 0


# --- Comparison vs standard tax --------------------------------------------------


class TestCompareVsStandardTax:
    async def test_high_margin_company_prefers_turnover_tax(self):
        """Turnover R1m, expenses R950k -> profit R50k: corporate 27% = R13,500 vs
        turnover tax R4,500 (3,500 + 2% of 50k)."""
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=1_000_000,
                estimated_annual_expenses_zar=950_000,
                entity_type=EntityType.company,
            )
        )
        assert result["turnover_tax"]["tax_zar"] == 4_500.0
        assert result["standard_tax"]["tax_zar"] == 13_500.0
        assert result["cheaper_option"] == "turnover_tax"
        assert result["saving_zar"] == 9_000.0

    async def test_thin_margin_company_prefers_standard_tax(self):
        """Turnover R2m, expenses R1.99m -> profit R10k: corporate R2,700 beats
        turnover tax R30,500 (12,500 + 3% of 600k)."""
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=2_000_000,
                estimated_annual_expenses_zar=1_990_000,
                entity_type=EntityType.company,
            )
        )
        assert result["turnover_tax"]["tax_zar"] == 30_500.0
        assert result["standard_tax"]["tax_zar"] == 2_700.0
        assert result["cheaper_option"] == "standard_tax"

    async def test_loss_making_business_still_pays_turnover_tax(self):
        """The key honesty case: profit is negative, standard tax is R0, but
        turnover tax of R2,000 (1% of 200k) is still due."""
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=800_000,
                estimated_annual_expenses_zar=900_000,
                entity_type=EntityType.sole_proprietor,
            )
        )
        assert result["profit_zar"] == -100_000.0
        assert result["standard_tax"]["tax_zar"] == 0.0
        assert result["turnover_tax"]["tax_zar"] == 2_000.0
        assert result["cheaper_option"] == "standard_tax"
        assert any("loss-making" in w for w in result["warnings"])

    async def test_sole_proprietor_gets_primary_rebate(self):
        """Profit R200k on the 2027 individual table: 18% = R36,000 less the
        R17,820 primary rebate -> R18,180. Turnover R500k is under the tax-free
        band so turnover tax is R0."""
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=500_000,
                estimated_annual_expenses_zar=300_000,
                entity_type=EntityType.sole_proprietor,
            )
        )
        assert result["standard_tax"]["tax_zar"] == 18_180.0
        assert result["turnover_tax"]["tax_zar"] == 0.0
        assert result["cheaper_option"] == "turnover_tax"

    async def test_company_gets_sbc_alternative_view(self):
        """Companies also get the 2027 SBC table view (own eligibility rules apply)."""
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=1_500_000,
                estimated_annual_expenses_zar=1_000_000,
                entity_type=EntityType.company,
            )
        )
        # profit 500k -> SBC: 18,620 + 21% of (500k - 365k) = 18,620 + 28,350 = 46,970
        assert result["sbc_alternative"]["tax_zar"] == 46_970.0

    async def test_sole_proprietor_has_no_sbc_view(self):
        result = await compare_vs_standard_tax(
            CompareInput(
                annual_turnover_zar=500_000,
                estimated_annual_expenses_zar=100_000,
                entity_type=EntityType.sole_proprietor,
            )
        )
        assert "sbc_alternative" not in result


# --- Status / structural ---------------------------------------------------------


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-turnover-tax-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert s["qualifying_limit_zar"] == 2_300_000.0
        assert s["last_rule_check"] == "2026-07"


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-turnover-tax-south-africa"
