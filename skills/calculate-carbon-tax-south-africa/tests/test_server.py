"""Tests for the calculate-carbon-tax-south-africa MCP server.

These tests pin the verified rates so we catch any drift if the constants change.
Verified 2026-07-30:
    National Treasury Budget 2026 Review Ch.4: carbon tax "increased from R236 to
    R308 per tonne of carbon dioxide equivalent from 1 January 2026"; carbon fuel
    levy 19c/l petrol, 23c/l diesel from 1 April 2026.
    SARS: allowances range 60%-95% (entity-specific; taken as input).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    CarbonTaxInput,
    FuelLevyInput,
    LiabilityInput,
    calculate_carbon_tax,
    check_liability,
    estimate_carbon_fuel_levy,
    get_status,
)

# --- Core calculation ------------------------------------------------------------


class TestCalculateCarbonTax:
    async def test_2026_rate_with_basic_allowance(self):
        """1,000 t at R308/t with the 60% typical minimum allowance:
        gross R308,000, payable R123,200, effective R123.20/t."""
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=1_000))
        assert out.calendar_year == 2026  # default is the current year
        assert out.headline_rate_per_tonne_zar == 308.0
        assert out.gross_carbon_tax_zar == 308_000.0
        assert out.carbon_tax_payable_zar == 123_200.0
        assert out.effective_rate_per_tonne_zar == 123.2

    async def test_max_allowance_95_percent(self):
        """1,000 t at 95% allowance -> effective R15.40/t -> R15,400."""
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=1_000, total_allowance_percent=95))
        assert out.carbon_tax_payable_zar == 15_400.0

    async def test_zero_allowance_full_rate(self):
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=1_000, total_allowance_percent=0))
        assert out.carbon_tax_payable_zar == 308_000.0
        # below the SARS-indicated 60% typical minimum -> extra warning
        assert any("typical minimum" in w for w in out.warnings)

    async def test_2025_rate_retained(self):
        """2025 emissions use R236/t: 1,000 t at 60% -> R94,400."""
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=1_000, calendar_year=2025))
        assert out.headline_rate_per_tonne_zar == 236.0
        assert out.carbon_tax_payable_zar == 94_400.0

    async def test_zero_emissions(self):
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=0))
        assert out.carbon_tax_payable_zar == 0.0

    async def test_requires_human_always(self):
        out = await calculate_carbon_tax(CarbonTaxInput(tonnes_co2e=500))
        assert out.requires_human is True
        assert any("practitioner" in s for s in out.human_steps)

    def test_allowance_above_95_rejected(self):
        """SARS caps the allowance range at 95% - higher input must be rejected."""
        with pytest.raises(ValidationError):
            CarbonTaxInput(tonnes_co2e=100, total_allowance_percent=96)

    def test_negative_tonnes_rejected(self):
        with pytest.raises(ValidationError):
            CarbonTaxInput(tonnes_co2e=-1)


# --- Scope / liability guidance --------------------------------------------------


class TestCheckLiability:
    async def test_no_emitting_activities_out_of_scope(self):
        result = await check_liability(LiabilityInput(conducts_emissions_generating_activities=False))
        assert result["scope_assessment"] == "out_of_scope"

    async def test_above_threshold_likely_liable(self):
        result = await check_liability(
            LiabilityInput(
                conducts_emissions_generating_activities=True,
                capacity_at_or_above_schedule_threshold=True,
            )
        )
        assert result["scope_assessment"] == "likely_liable"

    async def test_unknown_capacity_is_honest_about_it(self):
        """When capacity vs threshold is unknown, the tool says so instead of guessing."""
        result = await check_liability(LiabilityInput(conducts_emissions_generating_activities=True))
        assert result["scope_assessment"] == "unknown_needs_schedule_2_check"
        assert len(result["not_checked"]) > 0


# --- Carbon fuel levy ------------------------------------------------------------


class TestFuelLevy:
    async def test_petrol_and_diesel_rates(self):
        """1,000 l petrol (19c) + 1,000 l diesel (23c) = R190 + R230 = R420."""
        result = await estimate_carbon_fuel_levy(
            FuelLevyInput(monthly_petrol_litres=1_000, monthly_diesel_litres=1_000)
        )
        assert result["petrol_levy_zar"] == 190.0
        assert result["diesel_levy_zar"] == 230.0
        assert result["total_carbon_fuel_levy_zar"] == 420.0

    async def test_levy_is_flagged_as_included_at_pump(self):
        """Honesty pin: the output must say this is embedded in pump prices,
        not a separate payment."""
        result = await estimate_carbon_fuel_levy(FuelLevyInput(monthly_petrol_litres=100))
        assert "already included in pump prices" in result["important"]


# --- Status / structural ---------------------------------------------------------


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-carbon-tax-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert s["rate_2026_per_tonne_zar"] == 308.0
        assert "Schedule 2" in s["not_encoded"]


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-carbon-tax-south-africa"
