"""
MIA Skill: Register a private limited company in Kenya via BRS/eCitizen.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Wrap the Kenyan company registration flow: name search and reservation,
    incorporation forms, KRA PIN linkage - the first non-South-African jurisdiction in
    the library.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- https://brs.go.ke
- eCitizen (https://www.ecitizen.go.ke)

RESEARCH NOTES (honest gaps, not guesses):
    Current BRS fees, form names and processing timelines require research against live
    BRS/eCitizen sources - Kenyan figures are deliberately absent rather than guessed.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.register.company.kenya")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-register-company-kenya")


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
            "eCitizen identity onboarding; director KYC per Kenyan requirements",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the register-company-kenya "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_name_availability() -> NotImplementedOutput:
    """Search proposed company names against the BRS registry.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_name_availability",
        "Search proposed company names against the BRS registry.",
        (
            "BRS/eCitizen name-search automation - requires research into current BRS API "
            "availability vs browser flows"
        ),
    )


@mcp.tool()
async def prepare_registration() -> NotImplementedOutput:
    """Prepare the incorporation filing pack for eCitizen submission.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "prepare_registration",
        "Prepare the incorporation filing pack for eCitizen submission.",
        (
            "the current form set, fees and timelines - requires research on live BRS pages; no "
            "figures assumed"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "register-company-kenya",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Business Registration Service (BRS) via eCitizen",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_name_availability", "prepare_registration"],
        "primary_sources_to_verify": [
            "https://brs.go.ke",
            "eCitizen (https://www.ecitizen.go.ke)",
        ],
        "research_needed": (
            "Current BRS fees, form names and processing timelines require research against live "
            "BRS/eCitizen sources - Kenyan figures are deliberately absent rather than guessed."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
