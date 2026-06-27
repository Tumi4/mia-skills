"""Tests for the calculate-section-12b-solar-deduction MCP server.

These tests pin the real SARS rules so we catch any drift if the constants change.
Reference example (from public guidance): a R500,000 solar system for a company at
27% corporate rate yields a 100% (R500,000) deduction and ~R135,000 cash tax saving.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    DeductionInput,
    TaxpayerType,
    _marginal_rate_for_individual,
    _personal_tax,
    calculate_deduction,
    check_eligibility,
    compare_12b_vs_12ba,
    get_status,
)

# ─── Core calculation ───────────────────────────────────────────────────────────


class TestCalculateDeduction:
    async def test_company_500k_system_reference_case(self):
        """R500k equipment, company, healthy income → R500k deduction, R135k saving."""
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=500_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=2_000_000,
            )
        )
        assert out.success is True
        assert out.deduction_zar == 500_000.0  # 100% of qualifying cost
        assert out.cash_tax_saving_zar == 135_000.0  # 500k * 27%
        assert out.effective_net_cost_zar == 365_000.0  # 500k - 135k saving

    async def test_labour_excluded_from_deduction(self):
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=400_000,
                installation_labour_zar=100_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=2_000_000,
            )
        )
        # Deduction only on equipment, not labour
        assert out.deduction_zar == 400_000.0
        assert out.total_project_cost_zar == 500_000.0  # but total cost includes labour
        # saving = 400k * 27% = 108k
        assert out.cash_tax_saving_zar == 108_000.0

    async def test_grant_funded_portion_excluded(self):
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=1_000_000,
                grant_funded_portion_zar=500_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=5_000_000,
            )
        )
        # Only own-funded R500k qualifies
        assert out.qualifying_cost_zar == 500_000.0
        assert out.deduction_zar == 500_000.0
        assert any("grant" in w.lower() for w in out.warnings)

    async def test_deduction_exceeding_income_warns_company(self):
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=1_000_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=300_000,
            )
        )
        # Saving capped at absorbing only R300k of deduction
        assert out.cash_tax_saving_zar == pytest.approx(300_000 * 0.27)
        assert any("assessed loss" in w.lower() for w in out.warnings)

    async def test_individual_uses_marginal_rate(self):
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=200_000,
                taxpayer_type=TaxpayerType.individual,
                taxable_income_zar=2_000_000,  # top bracket, 45%
            )
        )
        # Top earner gets relief at 45% on the margin
        assert out.marginal_rate_used == 0.45
        assert out.cash_tax_saving_zar == pytest.approx(200_000 * 0.45, rel=0.01)

    async def test_requires_human_always_true(self):
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=100_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=500_000,
            )
        )
        assert out.requires_human is True
        assert any("Certificate of Compliance" in s for s in out.human_steps)


# ─── Edge cases: taxpayer types and boundary inputs ──────────────────────────────


class TestTaxpayerTypeEdgeCases:
    async def test_ordinary_trust_uses_flat_45_percent(self):
        """An ordinary trust is taxed at a flat 45%, NOT the progressive individual table.

        At R400k income an individual would sit on the 31% band; an ordinary trust must
        still get relief at 45%. This pins the trust fix (SARS flat trust rate).
        """
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=200_000,
                taxpayer_type=TaxpayerType.trust,
                taxable_income_zar=400_000,
            )
        )
        assert out.marginal_rate_used == 0.45
        assert out.cash_tax_saving_zar == 90_000.0  # 200k * 45%
        assert out.effective_net_cost_zar == 110_000.0

    async def test_special_trust_uses_individual_rates(self):
        """A special trust IS taxed on the individual brackets (unlike an ordinary trust)."""
        special = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=200_000,
                taxpayer_type=TaxpayerType.special_trust,
                taxable_income_zar=2_000_000,
            )
        )
        individual = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=200_000,
                taxpayer_type=TaxpayerType.individual,
                taxable_income_zar=2_000_000,
            )
        )
        assert special.marginal_rate_used == 0.45
        assert special.cash_tax_saving_zar == individual.cash_tax_saving_zar

    async def test_trust_deduction_exceeding_income_warns(self):
        """Ordinary trust: saving capped at absorbed income at 45%, with assessed-loss warning."""
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=1_000_000,
                taxpayer_type=TaxpayerType.trust,
                taxable_income_zar=300_000,
            )
        )
        assert out.cash_tax_saving_zar == pytest.approx(300_000 * 0.45)
        assert any("assessed loss" in w.lower() for w in out.warnings)

    async def test_grant_exceeding_equipment_cost_zeros_deduction(self):
        """A grant portion larger than the equipment cost leaves nothing to deduct."""
        out = await calculate_deduction(
            DeductionInput(
                equipment_cost_zar=500_000,
                grant_funded_portion_zar=600_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=2_000_000,
            )
        )
        assert out.qualifying_cost_zar == 0.0
        assert out.deduction_zar == 0.0
        assert out.cash_tax_saving_zar == 0.0

    def test_zero_taxable_income_is_rejected(self):
        """taxable_income_zar must be > 0 — zero/negative income is invalid input."""
        with pytest.raises(ValidationError):
            DeductionInput(
                equipment_cost_zar=100_000,
                taxpayer_type=TaxpayerType.company,
                taxable_income_zar=0,
            )


# ─── 12B vs 12BA comparison ─────────────────────────────────────────────────────


class TestCompare:
    async def test_comparison_shows_12ba_expired(self):
        result = await compare_12b_vs_12ba(
            equipment_cost_zar=500_000,
            taxpayer_type=TaxpayerType.company,
        )
        assert result["section_12b_live"]["deduction_zar"] == 500_000.0
        assert result["section_12ba_expired"]["deduction_zar"] == 625_000.0  # 125%
        assert "EXPIRED" in result["section_12ba_expired"]["status"]
        assert result["benefit_lost_to_expiry_zar"] > 0


# ─── Eligibility ────────────────────────────────────────────────────────────────


class TestEligibility:
    async def test_fully_eligible(self):
        result = await check_eligibility(
            is_business_use=True,
            owns_asset=True,
            has_certificate_of_compliance=True,
            is_new_and_unused=True,
            asset_type="solar_pv",
        )
        assert result["eligible"] is True
        assert result["blockers"] == []

    async def test_residential_use_blocked(self):
        result = await check_eligibility(
            is_business_use=False,
            owns_asset=True,
            has_certificate_of_compliance=True,
            is_new_and_unused=True,
        )
        assert result["eligible"] is False
        assert any("production of income" in b for b in result["blockers"])

    async def test_diesel_generator_blocked(self):
        result = await check_eligibility(
            is_business_use=True,
            owns_asset=True,
            has_certificate_of_compliance=True,
            is_new_and_unused=True,
            asset_type="diesel",
        )
        assert result["eligible"] is False
        assert any("fossil" in b.lower() for b in result["blockers"])

    async def test_missing_coc_blocked(self):
        result = await check_eligibility(
            is_business_use=True,
            owns_asset=True,
            has_certificate_of_compliance=False,
            is_new_and_unused=True,
        )
        assert result["eligible"] is False
        assert any("Certificate of Compliance" in b for b in result["blockers"])


# ─── Tax helpers ────────────────────────────────────────────────────────────────


class TestTaxHelpers:
    def test_marginal_rate_low_income(self):
        assert _marginal_rate_for_individual(100_000) == 0.18

    def test_marginal_rate_top_bracket(self):
        assert _marginal_rate_for_individual(2_000_000) == 0.45

    def test_personal_tax_is_monotonic(self):
        # More income should never mean less total tax
        prev = 0.0
        for income in [100_000, 300_000, 500_000, 800_000, 1_500_000, 2_500_000]:
            tax = _personal_tax(income)
            assert tax >= prev
            prev = tax


# ─── Status / structural ────────────────────────────────────────────────────────


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-section-12b-solar-deduction"
        assert s["status"] == "alpha"
        assert "calculate_deduction" in s["tools_working"]
        assert s["tools_stubbed"] == []


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-section-12b-solar-deduction"
