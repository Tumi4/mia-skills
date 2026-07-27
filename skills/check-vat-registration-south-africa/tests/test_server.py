"""Tests for the check-vat-registration-south-africa MCP server.

These tests pin the real SARS rules so we catch any drift if the constants change.
Verified on SARS 2026-07-27:
    VAT rate 15% (2025 proposed increases reversed 24 April 2025).
    Compulsory: > R2.3m taxable supplies in any consecutive 12 months (exceeded or
    likely to be exceeded), register within 21 business days. Was R1m before
    1 April 2026. Voluntary: past-12-month supplies exceed R120,000 (was R50,000).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (  # noqa: E402
    RegistrationCheckInput,
    VatPositionInput,
    check_registration_required,
    estimate_vat_position,
    get_status,
)

# --- Registration determination --------------------------------------------------


class TestMandatoryRegistration:
    async def test_past_supplies_over_threshold_mandatory(self):
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=2_400_000)
        )
        assert out.registration_type == "mandatory"
        assert out.registration_required is True
        assert "21 business days" in out.deadline_note

    async def test_exactly_at_threshold_not_mandatory(self):
        """SARS wording is 'exceeded ... R2.3 million' - exactly R2.3m does not exceed."""
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=2_300_000)
        )
        assert out.registration_required is False

    async def test_one_rand_over_threshold_mandatory(self):
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=2_300_001)
        )
        assert out.registration_required is True

    async def test_expected_future_supplies_trigger_mandatory(self):
        """The 'likely to exceed' leg: low past turnover, big signed pipeline."""
        out = await check_registration_required(
            RegistrationCheckInput(
                rolling_12m_taxable_supplies_zar=400_000,
                expected_next_12m_taxable_supplies_zar=2_500_000,
            )
        )
        assert out.registration_type == "mandatory"
        assert "coming 12 months" in out.deadline_note

    async def test_requires_human_always(self):
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=3_000_000)
        )
        assert out.requires_human is True
        assert any("eFiling" in s for s in out.human_steps)


class TestVoluntaryRegistration:
    async def test_over_voluntary_minimum_voluntary_available(self):
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=150_000)
        )
        assert out.registration_type == "voluntary_available"
        assert out.registration_required is False
        assert out.voluntary_registration_available is True

    async def test_exactly_at_voluntary_minimum_not_yet_eligible(self):
        """SARS wording is 'exceeded R120 000' - exactly R120,000 does not exceed."""
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=120_000)
        )
        assert out.registration_type == "not_yet_eligible"

    async def test_below_minimum_lists_alternative_routes(self):
        """Under R120k the alternative routes (R4,200/month, contracts, capex,
        Notices R446/R447) must be surfaced, not hidden."""
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=50_000)
        )
        assert out.registration_type == "not_yet_eligible"
        assert len(out.alternative_voluntary_routes) > 0
        assert any("4,200" in r for r in out.alternative_voluntary_routes)

    async def test_zero_turnover_startup(self):
        out = await check_registration_required(RegistrationCheckInput(rolling_12m_taxable_supplies_zar=0))
        assert out.success is True
        assert out.registration_type == "not_yet_eligible"


class TestTransitionalWarning:
    async def test_between_old_and_new_threshold_warns(self):
        """R1.5m is fine under the new R2.3m rule but exceeded the pre-April-2026
        R1m rule - the tool must flag the transitional question."""
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=1_500_000)
        )
        assert out.registration_required is False
        assert any("1 April 2026" in w for w in out.warnings)

    async def test_below_old_threshold_no_transitional_warning(self):
        out = await check_registration_required(
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=800_000)
        )
        assert out.warnings == []

    async def test_non_resident_electronic_services_noted(self):
        out = await check_registration_required(
            RegistrationCheckInput(
                rolling_12m_taxable_supplies_zar=500_000,
                is_non_resident_electronic_services_supplier=True,
            )
        )
        assert any("electronic services" in w for w in out.warnings)

    def test_negative_supplies_rejected(self):
        with pytest.raises(ValidationError):
            RegistrationCheckInput(rolling_12m_taxable_supplies_zar=-1)


# --- VAT position estimate -------------------------------------------------------


class TestEstimateVatPosition:
    async def test_payable_case_at_15_percent(self):
        """Sales R1m excl / purchases R600k excl -> output 150k, input 90k, pay 60k."""
        out = await estimate_vat_position(
            VatPositionInput(
                standard_rated_sales_excl_vat_zar=1_000_000,
                vatable_purchases_excl_vat_zar=600_000,
            )
        )
        assert out.vat_rate == 0.15
        assert out.output_vat_zar == 150_000.0
        assert out.input_vat_zar == 90_000.0
        assert out.net_vat_zar == 60_000.0
        assert out.position == "payable"

    async def test_refund_case(self):
        """Heavy input period (e.g. capex): purchases exceed sales -> refund."""
        out = await estimate_vat_position(
            VatPositionInput(
                standard_rated_sales_excl_vat_zar=200_000,
                vatable_purchases_excl_vat_zar=800_000,
            )
        )
        assert out.net_vat_zar == -90_000.0
        assert out.position == "refund"

    async def test_nil_position(self):
        out = await estimate_vat_position(
            VatPositionInput(
                standard_rated_sales_excl_vat_zar=0,
                vatable_purchases_excl_vat_zar=0,
            )
        )
        assert out.net_vat_zar == 0.0
        assert out.position == "nil"

    async def test_estimate_discloses_its_simplifications(self):
        """Honesty pin: the estimate must warn that zero-rated/exempt/denied inputs
        are not modelled."""
        out = await estimate_vat_position(
            VatPositionInput(
                standard_rated_sales_excl_vat_zar=100_000,
                vatable_purchases_excl_vat_zar=50_000,
            )
        )
        assert out.requires_human is True
        assert any("denied inputs" in w or "not modelled" in w for w in out.warnings)


# --- Status / structural ---------------------------------------------------------


class TestStatus:
    async def test_get_status(self):
        s = await get_status()
        assert s["skill"] == "check-vat-registration-south-africa"
        assert s["status"] == "alpha"
        assert s["tools_stubbed"] == []
        assert s["vat_rate"] == 0.15
        assert s["mandatory_threshold_zar"] == 2_300_000.0
        assert s["voluntary_minimum_zar"] == 120_000.0


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-check-vat-registration-south-africa"
