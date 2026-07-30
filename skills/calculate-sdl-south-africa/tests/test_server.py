"""Tests for the calculate-sdl-south-africa MCP server.

These tests pin the real SARS rules so we catch any drift if the constants change.
Verified on SARS 2026-07-30 (page last updated 15 Aug 2025):
    SDL = 1% of the leviable amount (salaries incl. wages, overtime, leave pay,
    bonuses, fees, commissions, lump sums). Exempt if expected leviable
    remuneration over the next 12 months won't exceed R500,000, plus specific
    public-sector / exempt-organisation categories.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    SdlCalculationInput,
    SdlLiabilityInput,
    calculate_sdl,
    check_sdl_liability,
    get_status,
)

# --- Calculation -----------------------------------------------------------------


class TestCalculateSdl:
    async def test_one_percent_of_leviable_amount(self):
        """R100,000 monthly payroll -> R1,000 SDL."""
        out = await calculate_sdl(SdlCalculationInput(monthly_leviable_amount_zar=100_000))
        assert out.sdl_rate == 0.01
        assert out.monthly_sdl_zar == 1_000.0
        assert out.possibly_exempt is False

    async def test_small_payroll_flags_possible_exemption(self):
        """R30,000 pm annualises to R360,000 - under the R500k threshold, so the
        tool must flag that SDL may not be due at all."""
        out = await calculate_sdl(SdlCalculationInput(monthly_leviable_amount_zar=30_000))
        assert out.monthly_sdl_zar == 300.0
        assert out.annualised_leviable_amount_zar == 360_000.0
        assert out.possibly_exempt is True
        assert any("exemption" in w for w in out.warnings)

    async def test_zero_payroll(self):
        out = await calculate_sdl(SdlCalculationInput(monthly_leviable_amount_zar=0))
        assert out.monthly_sdl_zar == 0.0
        assert out.warnings == []

    async def test_employer_cost_note(self):
        """SDL is an employer cost, never an employee deduction - the note says so."""
        out = await calculate_sdl(SdlCalculationInput(monthly_leviable_amount_zar=50_000))
        assert "EMPLOYER cost" in out.notes

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            SdlCalculationInput(monthly_leviable_amount_zar=-1)


# --- Liability / exemption -------------------------------------------------------


class TestSdlLiability:
    async def test_above_threshold_liable(self):
        out = await check_sdl_liability(SdlLiabilityInput(expected_total_remuneration_next_12m_zar=1_200_000))
        assert out.liable_for_sdl is True
        assert out.exemption_reasons == []

    async def test_exactly_at_threshold_exempt(self):
        """SARS wording: 'won't exceed R500 000' - exactly R500,000 does not exceed."""
        out = await check_sdl_liability(SdlLiabilityInput(expected_total_remuneration_next_12m_zar=500_000))
        assert out.liable_for_sdl is False

    async def test_one_rand_over_threshold_liable(self):
        out = await check_sdl_liability(SdlLiabilityInput(expected_total_remuneration_next_12m_zar=500_001))
        assert out.liable_for_sdl is True

    async def test_near_threshold_warns_about_forward_estimate(self):
        """R550,000 is liable but within 20% of the line - warn to document the
        forward-looking estimate."""
        out = await check_sdl_liability(SdlLiabilityInput(expected_total_remuneration_next_12m_zar=550_000))
        assert out.liable_for_sdl is True
        assert any("forward-looking" in w for w in out.warnings)

    async def test_well_above_threshold_no_estimate_warning(self):
        out = await check_sdl_liability(SdlLiabilityInput(expected_total_remuneration_next_12m_zar=2_000_000))
        assert out.warnings == []

    async def test_public_service_employer_exempt_regardless_of_size(self):
        out = await check_sdl_liability(
            SdlLiabilityInput(
                expected_total_remuneration_next_12m_zar=50_000_000,
                is_public_service_employer=True,
            )
        )
        assert out.liable_for_sdl is False
        assert any("Public service" in r for r in out.exemption_reasons)

    async def test_pbo_with_exemption_letter_exempt(self):
        out = await check_sdl_liability(
            SdlLiabilityInput(
                expected_total_remuneration_next_12m_zar=3_000_000,
                is_pbo_with_exemption_letter=True,
            )
        )
        assert out.liable_for_sdl is False

    def test_negative_remuneration_rejected(self):
        with pytest.raises(ValidationError):
            SdlLiabilityInput(expected_total_remuneration_next_12m_zar=-1)


# --- Status / structural ---------------------------------------------------------


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "calculate-sdl-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert s["sdl_rate"] == 0.01
        assert s["exemption_threshold_zar"] == 500_000.0


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-sdl-south-africa"
