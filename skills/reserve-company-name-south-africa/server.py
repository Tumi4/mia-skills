"""
MIA Skill: Reserve a company name with the South African CIPC (COR9.1 flow).

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Check availability of a proposed company name and reserve it with CIPC ahead of
    incorporation. Designed to be called standalone or internally by register-company-
    south-africa (composable-skills principle).

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- CIPC e-services (https://eservices.cipc.co.za)

RESEARCH NOTES (honest gaps, not guesses):
    Current CIPC name-reservation fee and reservation validity period require research
    on the live CIPC fee schedule - do not assume the commonly quoted figures.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.reserve.company.name")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-reserve-company-name-south-africa")


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
            "CIPC e-services account creation and login are browser-only today",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the reserve-company-name-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_name_availability() -> NotImplementedOutput:
    """Check whether a proposed company name is available with CIPC.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_name_availability",
        "Check whether a proposed company name is available with CIPC.",
        (
            "CIPC name search automation (Playwright) plus the name-rule checks (misleading names, "
            "trademark conflicts)"
        ),
    )


@mcp.tool()
async def reserve_name() -> NotImplementedOutput:
    """Reserve an available company name with CIPC (form COR9.1).

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "reserve_name",
        "Reserve an available company name with CIPC (form COR9.1).",
        (
            "the COR9.1 reservation flow, fees and reservation validity period - verify current fee "
            "and validity on CIPC before implementing"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "reserve-company-name-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Companies and Intellectual Property Commission (CIPC)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_name_availability", "reserve_name"],
        "primary_sources_to_verify": [
            "CIPC e-services (https://eservices.cipc.co.za)",
        ],
        "research_needed": (
            "Current CIPC name-reservation fee and reservation validity period require research on "
            "the live CIPC fee schedule - do not assume the commonly quoted figures."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
