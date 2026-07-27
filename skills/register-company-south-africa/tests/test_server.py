"""Tests for the register-company-south-africa MCP server."""

from __future__ import annotations

# Import the server module from parent directory
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    CompanyRegistration,
    Director,
    check_name_availability,
    estimate_costs,
    get_status,
    submit_registration,
)

# ─── Model validation tests ────────────────────────────────────────────────────


class TestDirectorValidation:
    def test_valid_director(self):
        d = Director(
            full_name="Tumelo Ncube",
            id_number="9001011234088",
            residential_address="123 Example Street, Cape Town, 8001",
            email="tumelo@example.com",
            phone="+27 82 555 1234",
        )
        assert d.nationality == "South African"  # default

    def test_rsa_id_must_be_13_digits(self):
        with pytest.raises(ValidationError):
            Director(
                full_name="Test User",
                id_number="123",  # too short
                residential_address="123 Example Street, Cape Town, 8001",
                email="test@example.com",
                phone="+27 82 555 1234",
            )

    def test_passport_number_allowed_for_foreign(self):
        d = Director(
            full_name="Foreign Director",
            id_number="P12345678",  # passport-style, not 13 digits
            nationality="Kenyan",
            residential_address="123 Example Street, Nairobi",
            email="foreign@example.com",
            phone="+254 700 123456",
        )
        assert d.nationality == "Kenyan"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            Director(
                full_name="Test User",
                id_number="9001011234088",
                residential_address="123 Example Street, Cape Town, 8001",
                email="not-an-email",
                phone="+27 82 555 1234",
            )


class TestCompanyRegistrationValidation:
    @pytest.fixture
    def valid_director(self) -> Director:
        return Director(
            full_name="Tumelo Ncube",
            id_number="9001011234088",
            residential_address="123 Example Street, Cape Town, 8001",
            email="tumelo@example.com",
            phone="+27 82 555 1234",
        )

    def test_valid_registration(self, valid_director: Director):
        reg = CompanyRegistration(
            company_name="Sunbright Holdings",
            directors=[valid_director],
            registered_address="123 Example Street, Cape Town, 8001",
            main_business_activity="Technology consulting and software development services",
        )
        assert reg.financial_year_end == "February"  # default
        assert reg.share_capital == 1000  # default

    def test_company_must_have_at_least_one_director(self):
        with pytest.raises(ValidationError):
            CompanyRegistration(
                company_name="No Directors Co",
                directors=[],
                registered_address="123 Example Street, Cape Town, 8001",
                main_business_activity="Some business activity here",
            )

    def test_max_four_name_alternatives(self, valid_director: Director):
        with pytest.raises(ValidationError):
            CompanyRegistration(
                company_name="Primary Name",
                name_alternatives=["Alt 1", "Alt 2", "Alt 3", "Alt 4", "Alt 5"],
                directors=[valid_director],
                registered_address="123 Example Street, Cape Town, 8001",
                main_business_activity="Some business activity here",
            )


# ─── Tool tests ────────────────────────────────────────────────────────────────


class TestEstimateCosts:
    async def test_default_estimate(self):
        result = await estimate_costs()
        assert result.success is True
        assert result.cost_estimate_zar == 225.0  # 175 + 50
        assert result.timeline_estimate_days == 14
        assert result.result is not None
        assert "breakdown_zar" in result.result

    async def test_breakdown_includes_all_components(self):
        result = await estimate_costs(num_directors=3, include_bee_certificate=True)
        assert result.result is not None
        breakdown = result.result["breakdown_zar"]
        assert "cipc_registration" in breakdown
        assert "name_reservation" in breakdown
        assert "bee_certificate" in breakdown
        assert "tax_registration" in breakdown


class TestGetStatus:
    async def test_returns_skill_metadata(self):
        result = await get_status()
        assert result["skill"] == "register-company-south-africa"
        assert result["version"] == "0.1.0"
        assert result["status"] == "scaffold"
        assert "next_milestones" in result
        assert len(result["next_milestones"]) > 0


class TestStubBehavior:
    """Tests that document current stub behavior so we know when it changes."""

    async def test_check_name_returns_stub_response(self):
        result = await check_name_availability("Test Company Pty Ltd")
        # Will return error if no credentials set, otherwise stub success
        # Either way, the call should not raise
        assert result.notes != ""

    async def test_submit_registration_dry_run_default(self):
        result = await submit_registration("Test Co")
        assert result.result is not None
        assert result.result["dry_run"] is True
        assert "confirm_irreversible=True" in result.notes


# ─── Structural test ───────────────────────────────────────────────────────────


def test_mcp_server_starts():
    """Sanity check: importing server.py should register tools without error."""
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-register-company-south-africa"
