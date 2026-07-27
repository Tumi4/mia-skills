"""
MIA Skill: Calculate South African carbon tax liability for emitting activities.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Determine whether an entity's activities trigger carbon tax, and calculate the
    liability from emissions data using the current rate per tonne CO2e and the
    applicable allowances (basic, trade-exposure, performance) - directly aligned with
    MIA's climate focus.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- SARS carbon tax pages (https://www.sars.gov.za/customs-and-excise/excise/environmental-levy-products/carbon-tax/)

RESEARCH NOTES (honest gaps, not guesses):
    The current carbon tax rate per tonne CO2e (it escalates annually), phase rules and
    allowance percentages require research against live SARS pages before any constant
    is coded.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.calculate.carbon.tax")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-calculate-carbon-tax-south-africa")


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
            (
                "Carbon tax registration and accounts run via SARS excise; emissions data needs a "
                "competent person"
            ),
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the calculate-carbon-tax-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_liability() -> NotImplementedOutput:
    """Determine whether activities fall within carbon tax scope.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_liability",
        "Determine whether activities fall within carbon tax scope.",
        "the Schedule 2 activity/threshold list - requires research on the live SARS/DFFE sources",
    )


@mcp.tool()
async def calculate_carbon_tax() -> NotImplementedOutput:
    """Calculate carbon tax from tonnes CO2e and applicable allowances.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "calculate_carbon_tax",
        "Calculate carbon tax from tonnes CO2e and applicable allowances.",
        (
            "the CURRENT rate per tonne and allowance percentages - the rate escalates annually and "
            "requires research on the live SARS page; figures must not be guessed"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "calculate-carbon-tax-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "South African Revenue Service (SARS)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_liability", "calculate_carbon_tax"],
        "primary_sources_to_verify": [
            (
                "SARS carbon tax pages (https://www.sars.gov.za/customs-and-excise/excise/environmental- "
                "levy-products/carbon-tax/)"
            ),
        ],
        "research_needed": (
            "The current carbon tax rate per tonne CO2e (it escalates annually), phase rules and "
            "allowance percentages require research against live SARS pages before any constant is "
            "coded."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
