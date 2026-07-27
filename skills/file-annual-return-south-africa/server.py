"""
MIA Skill: File a company annual return with the South African CIPC.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Determine when a company's CIPC annual return is due, calculate the filing fee from
    turnover bands, and prepare/submit the return - the filing every SA company must
    make yearly or face deregistration.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- CIPC annual returns portal (https://annualreturns.cipc.co.za)

RESEARCH NOTES (honest gaps, not guesses):
    The CIPC annual-return fee table (turnover bands and amounts) and late-filing
    penalties require research against the live CIPC schedule.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.file.annual.return")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-file-annual-return-south-africa")


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
            ("Annual financial statements or FAS may need to accompany the return depending on company type"),
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the file-annual-return-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_due_date() -> NotImplementedOutput:
    """Determine the annual-return window from the company's registration anniversary.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_due_date",
        "Determine the annual-return window from the company's registration anniversary.",
        "the due-window rules and late-penalty structure - verify on CIPC",
    )


@mcp.tool()
async def calculate_filing_fee() -> NotImplementedOutput:
    """Calculate the annual return fee from the company's turnover band.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "calculate_filing_fee",
        "Calculate the annual return fee from the company's turnover band.",
        (
            "the CIPC turnover-band fee table - requires research on the live CIPC fee schedule; "
            "figures must not be guessed"
        ),
    )


@mcp.tool()
async def file_annual_return() -> NotImplementedOutput:
    """Submit the annual return via the CIPC portal.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "file_annual_return",
        "Submit the annual return via the CIPC portal.",
        "portal automation (Playwright) with an explicit confirm-before-submit step",
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "file-annual-return-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Companies and Intellectual Property Commission (CIPC)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_due_date", "calculate_filing_fee", "file_annual_return"],
        "primary_sources_to_verify": [
            "CIPC annual returns portal (https://annualreturns.cipc.co.za)",
        ],
        "research_needed": (
            "The CIPC annual-return fee table (turnover bands and amounts) and late-filing penalties "
            "require research against the live CIPC schedule."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
