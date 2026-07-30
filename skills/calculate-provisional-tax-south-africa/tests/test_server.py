"""Tests for the calculate-provisional-tax-south-africa MCP server.

These tests pin the real SARS rules so we catch any drift if the constants change.
Verified 2026-07-30 against the SARS provisional tax page (29 Jun 2026) and the
Guide for Provisional Tax GEN-PT-01-G01 (effective 29 Jun 2026):
    Period 1 = half of full-year tax less credits; period 2 = full-year tax less
    credits and the first payment. Second-period accuracy: 90% (<= R1m, with the
    basic-amount alternative) / 80% (> R1m); 20% underestimation penalty; basic
    amount = last assessed income less taxable capital gain, +8% after 18 months.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    BasicAmountInput,
    ProvisionalPaymentInput,
    TaxpayerStatusInput,
    UnderestimationInput,
    calculate_basic_amount,
    calculate_provisional_payment,
    check_provisional_taxpayer_status,
    check_underestimation_penalty,
    get_status,
)

# --- Provisional taxpayer status -------------------------------------------------


class TestTaxpayerStatus:
    async def test_salary_only_not_provisional(self):
        result = await check_provisional_taxpayer_status(
            TaxpayerStatusInput(receives_income_other_than_remuneration=False)
        )
        assert result["is_provisional_taxpayer"] is False

    async def test_company_is_provisional(self):
        result = await check_provisional_taxpayer_status(
            TaxpayerStatusInput(receives_income_other_than_remuneration=True, is_natural_person=False)
        )
        assert result["is_provisional_taxpayer"] is True

    async def test_business_income_makes_natural_person_provisional(self):
        result = await check_provisional_taxpayer_status(
            TaxpayerStatusInput(
                receives_income_other_than_remuneration=True,
                carries_on_business=True,
                expected_taxable_income_zar=80_000,  # even under the threshold
            )
        )
        assert result["is_provisional_taxpayer"] is True

    async def test_small_interest_income_excluded_by_r30k_rule(self):
        """Salaried person with R25k interest: other income <= R30,000 -> excluded."""
        result = await check_provisional_taxpayer_status(
            TaxpayerStatusInput(
                receives_income_other_than_remuneration=True,
                expected_taxable_income_zar=400_000,
                other_income_zar=25_000,
            )
        )
        assert result["is_provisional_taxpayer"] is False
        assert "30,000" in result["reason"]

    async def test_pensioner_under_65plus_threshold_excluded(self):
        """68-year-old, no business, taxable R150,000 <= R153,250 threshold."""
        result = await check_provisional_taxpayer_status(
            TaxpayerStatusInput(
                receives_income_other_than_remuneration=True,
                expected_taxable_income_zar=150_000,
                other_income_zar=150_000,  # over R30k, so threshold leg does the work
                age=68,
            )
        )
        assert result["is_provisional_taxpayer"] is False


# --- Payment calculations --------------------------------------------------------


class TestProvisionalPayments:
    async def test_first_period_company_half_of_annual(self):
        """Company estimating R1m: annual 27% = R270,000 -> period 1 = R135,000."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(period=1, entity_type="company", estimated_taxable_income_zar=1_000_000)
        )
        assert result["full_year_tax_zar"] == 270_000.0
        assert result["provisional_payment_zar"] == 135_000.0

    async def test_first_period_individual_2027_table(self):
        """Individual, R500,000 estimate, age 40: tax 116,237 - 17,820 = 98,417
        -> period 1 = R49,208.50."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(period=1, entity_type="individual", estimated_taxable_income_zar=500_000)
        )
        assert result["full_year_tax_zar"] == 98_417.0
        assert result["provisional_payment_zar"] == 49_208.5

    async def test_second_period_deducts_first_payment(self):
        """Company R1m: period 2 = 270,000 - 135,000 first payment = 135,000."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(
                period=2,
                entity_type="company",
                estimated_taxable_income_zar=1_000_000,
                first_period_payment_zar=135_000,
            )
        )
        assert result["provisional_payment_zar"] == 135_000.0

    async def test_second_period_deducts_paye_and_first_payment(self):
        """Individual R600,000: tax 132,907; less PAYE 50,000 and P1 20,000 = 62,907."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(
                period=2,
                entity_type="individual",
                estimated_taxable_income_zar=600_000,
                employees_tax_zar=50_000,
                first_period_payment_zar=20_000,
            )
        )
        assert result["full_year_tax_zar"] == 132_907.0
        assert result["provisional_payment_zar"] == 62_907.0

    async def test_trust_flat_45_percent(self):
        """Ordinary trust R400,000: annual 45% = 180,000 -> period 1 = 90,000."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(period=1, entity_type="trust", estimated_taxable_income_zar=400_000)
        )
        assert result["provisional_payment_zar"] == 90_000.0

    async def test_payment_floors_at_zero(self):
        """Credits exceeding the liability never produce a negative payment."""
        result = await calculate_provisional_payment(
            ProvisionalPaymentInput(
                period=2,
                entity_type="company",
                estimated_taxable_income_zar=100_000,
                employees_tax_zar=50_000,
                first_period_payment_zar=50_000,
            )
        )
        assert result["provisional_payment_zar"] == 0.0


# --- Underestimation penalty -----------------------------------------------------


class TestUnderestimationPenalty:
    async def test_at_or_below_1m_triggered_below_both_legs(self):
        """Company: actual 800k, estimate 600k, basic 700k, paid 150k.
        90% of actual = 720k; estimate below both -> base = min(tax(720k), tax(700k))
        = 189,000 -> penalty 20% x 39,000 = 7,800."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=800_000,
                second_period_estimate_zar=600_000,
                entity_type="company",
                employees_tax_plus_provisional_paid_zar=150_000,
                basic_amount_zar=700_000,
            )
        )
        assert result["penalty_triggered"] is True
        assert result["estimated_penalty_zar"] == 7_800.0

    async def test_at_or_below_1m_saved_by_basic_amount(self):
        """Estimate equals the basic amount: below 90% of actual but NOT below the
        basic amount -> no penalty (the basic-amount safe harbour)."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=800_000,
                second_period_estimate_zar=700_000,
                entity_type="company",
                employees_tax_plus_provisional_paid_zar=150_000,
                basic_amount_zar=700_000,
            )
        )
        assert result["penalty_triggered"] is False
        assert result["estimated_penalty_zar"] == 0.0

    async def test_missing_basic_amount_is_disclosed(self):
        """Without the basic amount the tool assumes the worst and says so."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=800_000,
                second_period_estimate_zar=600_000,
                entity_type="company",
                employees_tax_plus_provisional_paid_zar=150_000,
            )
        )
        assert result["penalty_triggered"] is True
        assert any("Basic amount not supplied" in w for w in result["warnings"])

    async def test_above_1m_uses_80_percent_rule(self):
        """Company: actual 2m, estimate 1.5m < 80% (1.6m), paid 400k.
        Base = tax(1.6m) = 432,000 -> penalty 20% x 32,000 = 6,400."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=2_000_000,
                second_period_estimate_zar=1_500_000,
                entity_type="company",
                employees_tax_plus_provisional_paid_zar=400_000,
            )
        )
        assert result["penalty_triggered"] is True
        assert result["estimated_penalty_zar"] == 6_400.0

    async def test_above_1m_at_80_percent_not_triggered(self):
        """Estimate exactly at 80% of actual is not below it -> no penalty."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=2_000_000,
                second_period_estimate_zar=1_600_000,
                entity_type="company",
            )
        )
        assert result["penalty_triggered"] is False

    async def test_penalty_never_negative(self):
        """Payments exceeding the penalty base floor the penalty at zero."""
        result = await check_underestimation_penalty(
            UnderestimationInput(
                actual_taxable_income_zar=2_000_000,
                second_period_estimate_zar=1_000_000,
                entity_type="company",
                employees_tax_plus_provisional_paid_zar=500_000,  # > tax on 1.6m (432k)
            )
        )
        assert result["penalty_triggered"] is True
        assert result["estimated_penalty_zar"] == 0.0


# --- Basic amount ----------------------------------------------------------------


class TestBasicAmount:
    async def test_capital_gain_excluded_no_escalation(self):
        """R500k assessed less R50k capital gain, 12 months -> R450,000."""
        result = await calculate_basic_amount(
            BasicAmountInput(
                last_assessed_taxable_income_zar=500_000,
                taxable_capital_gain_in_that_year_zar=50_000,
                months_since_end_of_that_year=12,
            )
        )
        assert result["basic_amount_zar"] == 450_000.0
        assert result["escalation_applied"] is False

    async def test_escalation_after_18_months(self):
        """Same figures at 20 months -> 450,000 x 1.08 = 486,000."""
        result = await calculate_basic_amount(
            BasicAmountInput(
                last_assessed_taxable_income_zar=500_000,
                taxable_capital_gain_in_that_year_zar=50_000,
                months_since_end_of_that_year=20,
            )
        )
        assert result["basic_amount_zar"] == 486_000.0
        assert result["escalation_applied"] is True

    async def test_exactly_18_months_no_escalation(self):
        """The rule is MORE than 18 months - exactly 18 does not escalate."""
        result = await calculate_basic_amount(
            BasicAmountInput(
                last_assessed_taxable_income_zar=300_000,
                months_since_end_of_that_year=18,
            )
        )
        assert result["basic_amount_zar"] == 300_000.0
        assert result["escalation_applied"] is False


# --- Validation / structural -----------------------------------------------------


class TestValidation:
    def test_negative_income_rejected(self):
        with pytest.raises(ValidationError):
            UnderestimationInput(actual_taxable_income_zar=-1, second_period_estimate_zar=0)

    def test_invalid_period_rejected(self):
        with pytest.raises(ValidationError):
            ProvisionalPaymentInput(period=3, estimated_taxable_income_zar=100_000)


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-provisional-tax-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert "Special trusts" in s["not_modelled"]


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-provisional-tax-south-africa"
