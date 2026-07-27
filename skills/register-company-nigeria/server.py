"""
MIA Skill: Register a private limited company in Nigeria via the CAC.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Wrap the Nigerian company registration flow on the CAC portal: name reservation,
    incorporation, TIN issuance - alongside Kenya, the start of the library's pan-
    African coverage.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- https://www.cac.gov.ng
- CAC company registration portal

RESEARCH NOTES (honest gaps, not guesses):
    Current CAC fees, stamp-duty treatment, form names and timelines require research
    against live CAC sources - Nigerian figures are deliberately absent rather than
    guessed.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.register.company.nigeria")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-register-company-nigeria")


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
            "Director identification (NIN) and any attestation requirements per current CAC practice",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the register-company-nigeria "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_name_availability() -> NotImplementedOutput:
    """Search proposed company names against the CAC registry.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_name_availability",
        "Search proposed company names against the CAC registry.",
        "CAC portal automation - requires research into the current public-search and reservation flow",
    )


@mcp.tool()
async def prepare_registration() -> NotImplementedOutput:
    """Prepare the CAC incorporation filing pack.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "prepare_registration",
        "Prepare the CAC incorporation filing pack.",
        (
            "the current CAC form set, fees (incl. stamp duty) and timelines - requires research on "
            "live CAC sources; no figures assumed"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "register-company-nigeria",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Corporate Affairs Commission (CAC)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_name_availability", "prepare_registration"],
        "primary_sources_to_verify": [
            "https://www.cac.gov.ng",
            "CAC company registration portal",
        ],
        "research_needed": (
            "Current CAC fees, stamp-duty treatment, form names and timelines require research "
            "against live CAC sources - Nigerian figures are deliberately absent rather than guessed."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
