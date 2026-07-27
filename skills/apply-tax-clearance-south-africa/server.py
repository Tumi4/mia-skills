"""
MIA Skill: Apply for a SARS Tax Compliance Status (tax clearance) PIN.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Request and share a Tax Compliance Status (TCS) PIN - required for tenders, some
    contracts and foreign investment allowances. Checks readiness (returns filed, no
    debt) before applying via eFiling.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- SARS Tax Compliance Status pages (https://www.sars.gov.za)

RESEARCH NOTES (honest gaps, not guesses):
    Current TCS request types and their criteria require research on the live SARS TCS
    pages.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.apply.tax.clearance")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-apply-tax-clearance-south-africa")


class NotImplementedOutput(BaseModel):
    """Structured response every stub returns - honest, machine-readable."""

    success: bool = False
    implemented: bool = False
    skill_status: str = "scaffold"
    requires_human: bool = True
    human_steps: list[str] = []
    what_this_will_do: str = ""
    needs_before_implementation: str = ""
    notes: str = ""


def _stub(tool: str, will_do: str, needs: str) -> NotImplementedOutput:
    logger.info("%s called on scaffold skill - returning not-implemented", tool)
    return NotImplementedOutput(
        human_steps=[
            "Outstanding returns or tax debt must be resolved by a human before a TCS PIN will issue",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the apply-tax-clearance-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_compliance_readiness() -> NotImplementedOutput:
    """Pre-check the common blockers to a compliant TCS (outstanding returns, debt).

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_compliance_readiness",
        "Pre-check the common blockers to a compliant TCS (outstanding returns, debt).",
        (
            "eFiling status reads - requires research into the current TCS request types (good "
            "standing, tender, FIA/emigration)"
        ),
    )


@mcp.tool()
async def request_tcs_pin() -> NotImplementedOutput:
    """Request the Tax Compliance Status PIN via eFiling.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "request_tcs_pin",
        "Request the Tax Compliance Status PIN via eFiling.",
        (
            "eFiling automation - SARS eFiling is browser-only with hCaptcha; captcha means "
            "requires_human per the browser-automation policy"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "apply-tax-clearance-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "South African Revenue Service (SARS)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_compliance_readiness", "request_tcs_pin"],
        "primary_sources_to_verify": [
            "SARS Tax Compliance Status pages (https://www.sars.gov.za)",
        ],
        "research_needed": (
            "Current TCS request types and their criteria require research on the live SARS TCS pages."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
