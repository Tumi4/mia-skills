"""
MIA Skill: Register a Pty Ltd company in South Africa.

Wraps the Companies and Intellectual Property Commission (CIPC) company registration
process. Most of CIPC's operations are not API-exposed; this skill uses Playwright
browser automation against the CIPC e-services portal where APIs are not available.

Status: scaffold (v0.1.0). Tool signatures are stable; underlying implementations
are stubs and clearly marked. Wire up the real integrations in the order listed
in the `next_milestones` field returned by `get_status`.

Requires (env vars):
    CIPC_USERNAME — your CIPC e-services account username
    CIPC_PASSWORD — your CIPC e-services account password

Usage:
    python server.py

Then connect from any MCP-compatible client (Claude Desktop, Cursor, custom agent).
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, EmailStr, Field, field_validator

# ─── Setup ─────────────────────────────────────────────────────────────────────

logger = logging.getLogger("mia.register-company-sa")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-register-company-south-africa")

# ─── Models ────────────────────────────────────────────────────────────────────


class Director(BaseModel):
    """A director of the proposed company."""

    full_name: str = Field(..., min_length=2, description="Full legal name as on ID")
    id_number: str = Field(
        ..., description="13-digit RSA ID or passport number for foreign nationals"
    )
    nationality: str = Field(default="South African")
    residential_address: str = Field(..., min_length=10)
    email: EmailStr
    phone: str = Field(..., description="Including country code, e.g. +27 82 123 4567")

    @field_validator("id_number")
    @classmethod
    def validate_id_number(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        # RSA IDs are 13 digits. Passports vary.
        if v.isdigit() and len(v) != 13:
            raise ValueError("RSA ID numbers must be exactly 13 digits")
        return v


class CompanyRegistration(BaseModel):
    """All inputs required to register a Pty Ltd."""

    company_name: str = Field(..., min_length=2, max_length=120)
    name_alternatives: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Up to 4 backup names if first choice is taken. CIPC allows 4 total.",
    )
    directors: list[Director] = Field(..., min_length=1, max_length=20)
    registered_address: str = Field(..., min_length=10)
    financial_year_end: Literal["February", "June", "December"] = "February"
    share_capital: int = Field(
        default=1000, ge=1, description="Number of ordinary shares to authorize"
    )
    main_business_activity: str = Field(
        ..., min_length=10, description="One sentence describing the business"
    )


# ─── Standard output envelope ──────────────────────────────────────────────────


class StandardOutput(BaseModel):
    success: bool
    result: dict | None = None
    requires_human: bool = False
    human_steps: list[str] = []
    next_actions: list[str] = []
    cost_estimate_zar: float | None = None
    timeline_estimate_days: int | None = None
    notes: str = ""


# ─── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def check_name_availability(name: str) -> StandardOutput:
    """Check if a proposed company name is available for reservation with CIPC.

    Hits the CIPC name reservation system. CIPC requires that a name not be:
    - Already registered or reserved
    - Misleading (e.g. implying government endorsement)
    - Identical to an existing trademark

    Limits:
    - Requires valid CIPC e-services credentials in env (CIPC_USERNAME, CIPC_PASSWORD)
    - Does not reserve the name (use `reserve_name` for that)
    - Rate-limited by CIPC; do not call in tight loops

    Implementation status: STUB. Wire up Playwright against
    https://eservices.cipc.co.za/Account.aspx
    """
    logger.info("check_name_availability called for: %s", name)

    if not (os.getenv("CIPC_USERNAME") and os.getenv("CIPC_PASSWORD")):
        return StandardOutput(
            success=False,
            requires_human=True,
            human_steps=["Set CIPC_USERNAME and CIPC_PASSWORD environment variables"],
            notes="CIPC credentials not configured.",
        )

    # TODO: real implementation via Playwright
    return StandardOutput(
        success=True,
        result={"name": name, "available": True, "similar_names_existing": []},
        next_actions=["reserve_name"],
        cost_estimate_zar=50.0,
        timeline_estimate_days=1,
        notes="STUB IMPLEMENTATION. Returns optimistic placeholder. Replace with real CIPC check.",
    )


@mcp.tool()
async def reserve_name(name: str, applicant_id: str) -> StandardOutput:
    """Reserve an available name with CIPC. Reservation is valid for 6 months.

    Implementation status: STUB.
    """
    logger.info("reserve_name called for: %s", name)
    return StandardOutput(
        success=False,
        requires_human=True,
        human_steps=[
            "Log in to CIPC e-services",
            "Navigate to Name Reservation",
            "Submit form COR9.1 with this name",
        ],
        cost_estimate_zar=50.0,
        timeline_estimate_days=2,
        notes="STUB IMPLEMENTATION. Reservation flow not yet automated.",
    )


@mcp.tool()
async def estimate_costs(
    num_directors: int = 1,
    include_bee_certificate: bool = True,
    include_tax_registration: bool = True,
) -> StandardOutput:
    """Estimate total cost in ZAR for registering a Pty Ltd including ancillary services.

    Returns CIPC fees, name reservation, B-BBEE EME certificate, and SARS tax registration.
    """
    cipc_registration = 175.0
    name_reservation = 50.0
    # EME certificates are free below the EME turnover threshold
    bee_certificate = 0.0 if include_bee_certificate else 0.0
    tax_registration = 0.0 if include_tax_registration else 0.0  # automatic via CIPC

    total = cipc_registration + name_reservation + bee_certificate + tax_registration

    return StandardOutput(
        success=True,
        result={
            "breakdown_zar": {
                "cipc_registration": cipc_registration,
                "name_reservation": name_reservation,
                "bee_certificate": bee_certificate,
                "tax_registration": tax_registration,
            },
            "total_zar": total,
            "num_directors": num_directors,
        },
        cost_estimate_zar=total,
        timeline_estimate_days=14,
        notes=(
            "Cost estimates exclude optional services (registered office address, "
            "company secretary, accounting setup). Add ~R3,000–R8,000/year for those."
        ),
    )


@mcp.tool()
async def prepare_filing(registration: CompanyRegistration) -> StandardOutput:
    """Validate inputs and prepare all documents required for CIPC filing.

    Generates:
    - Memorandum of Incorporation (MOI) — Form CoR15.1A (standard short form)
    - Notice of Incorporation — Form CoR14.1
    - Director consent letters
    - B-BBEE EME affidavit (template)

    Returns a checklist of what's ready and what still needs human action.

    Implementation status: STUB. Document generation logic to be implemented.
    """
    logger.info("prepare_filing called for company: %s", registration.company_name)

    # Real implementation will:
    # 1. Validate that name has been reserved (call check_reservation_status)
    # 2. Generate MOI (CoR15.1A) PDF from template
    # 3. Generate CoR14.1 from template
    # 4. Generate director consent letters per director
    # 5. Generate BEE EME affidavit template

    checklist = {
        "name_reserved": False,
        "moi_cor15_1a_generated": False,
        "notice_cor14_1_generated": False,
        "director_consents_generated": False,
        "bee_eme_affidavit_template_generated": False,
        "registered_address_verified": False,
        "share_certificate_template_generated": False,
    }

    return StandardOutput(
        success=False,
        result={"checklist": checklist, "company_name": registration.company_name},
        requires_human=True,
        human_steps=[
            "All directors must sign the MOI before a Commissioner of Oaths",
            "B-BBEE EME affidavit must be sworn before a Commissioner of Oaths",
            "Director ID verification (in person or via accredited verifier)",
        ],
        next_actions=["submit_registration"],
        cost_estimate_zar=225.0,
        timeline_estimate_days=14,
        notes="STUB IMPLEMENTATION. Document generation not yet implemented.",
    )


@mcp.tool()
async def submit_registration(
    company_name: str,
    confirm_irreversible: bool = False,
) -> StandardOutput:
    """Submit the prepared filing to CIPC. THIS IS AN IRREVERSIBLE ACTION.

    Requires `confirm_irreversible=True` to actually submit. Otherwise returns
    a dry-run summary of what would be submitted.

    Implementation status: STUB.
    """
    if not confirm_irreversible:
        return StandardOutput(
            success=True,
            result={"dry_run": True, "company_name": company_name},
            notes=(
                "Dry run. To actually submit, call again with confirm_irreversible=True. "
                "Note: registration cost (R175 + R50 name reservation) is non-refundable."
            ),
        )

    return StandardOutput(
        success=False,
        requires_human=True,
        human_steps=["Log in to CIPC e-services and submit manually for now"],
        notes="STUB IMPLEMENTATION. Real submission flow not yet automated.",
    )


@mcp.tool()
async def check_registration_status(tracking_number: str) -> StandardOutput:
    """Check the status of a submitted CIPC registration by tracking number.

    Implementation status: STUB.
    """
    return StandardOutput(
        success=False,
        result={"tracking_number": tracking_number, "status": "unknown"},
        notes="STUB IMPLEMENTATION.",
    )


@mcp.tool()
async def get_status() -> dict:
    """Get current implementation status of this skill. Useful for clients
    to understand what's wired up versus stubbed.
    """
    return {
        "skill": "register-company-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "tools_stubbed": [
            "check_name_availability",
            "reserve_name",
            "prepare_filing",
            "submit_registration",
            "check_registration_status",
        ],
        "tools_working": ["estimate_costs", "get_status"],
        "next_milestones": [
            "Implement CIPC e-services login flow via Playwright",
            "Implement check_name_availability against real CIPC system",
            "Generate MOI (CoR15.1A) PDF from Pydantic input model",
            "Implement reserve_name flow with confirmation step",
            "Implement prepare_filing document bundle",
            "Add tests against CIPC sandbox if/when available",
        ],
        "estimated_full_implementation_weeks": 6,
    }


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
