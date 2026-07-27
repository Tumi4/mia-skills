"""
MIA Skill: Check a small business's eligibility for SEDA support programmes and SEFA funding instruments.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Map a business's profile (stage, sector, turnover, ownership) against live SEDA
    programmes and SEFA funding instruments, returning which are worth applying to and
    what each requires.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- https://www.seda.org.za
- https://www.sefa.org.za

RESEARCH NOTES (honest gaps, not guesses):
    The live SEDA programme list and SEFA instrument criteria require research - both
    change often enough that a static snapshot without a last-verified date would be
    dishonest.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.check.grant.eligibility.seda.sefa")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-check-grant-eligibility-seda-sefa")


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
            "Applications themselves run through SEDA/SEFA offices and portals with human assessment",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the check-grant-eligibility-seda-sefa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def list_programmes() -> NotImplementedOutput:
    """List current SEDA programmes and SEFA instruments with their criteria.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "list_programmes",
        "List current SEDA programmes and SEFA instruments with their criteria.",
        (
            "a maintained programme dataset - requires research; programmes change frequently and "
            "must not be hardcoded from memory"
        ),
    )


@mcp.tool()
async def check_eligibility() -> NotImplementedOutput:
    """Match a business profile against programme criteria.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_eligibility",
        "Match a business profile against programme criteria.",
        "the eligibility rule engine over the researched programme dataset",
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "check-grant-eligibility-seda-sefa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Small Enterprise Development Agency (SEDA) and Small Enterprise Finance Agency (SEFA)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["list_programmes", "check_eligibility"],
        "primary_sources_to_verify": [
            "https://www.seda.org.za",
            "https://www.sefa.org.za",
        ],
        "research_needed": (
            "The live SEDA programme list and SEFA instrument criteria require research - both change "
            "often enough that a static snapshot without a last-verified date would be dishonest."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
