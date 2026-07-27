"""
MIA Skill: Look up AfCFTA preferential tariff treatment and rules of origin for a product and trade lane.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Given an HS code, origin and destination state party, return the AfCFTA preferential
    rate vs MFN, the applicable rules of origin, and the certificate-of-origin
    requirements - turning the continent's flagship trade deal into a callable tool.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- AfCFTA e-Tariff Book (https://au-afcfta.org)
- national customs schedules

RESEARCH NOTES (honest gaps, not guesses):
    Tariff phase-down schedules differ per state party and product; several rules-of-
    origin chapters remain under negotiation - all of it requires research against the
    AfCFTA e-Tariff Book rather than assumption.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.lookup.afcfta.tariff.preference")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-lookup-afcfta-tariff-preference")


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
                "Certificates of origin are issued by national designated authorities - a "
                "human/institutional step"
            ),
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the lookup-afcfta-tariff-preference "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def lookup_tariff_preference() -> NotImplementedOutput:
    """Look up the AfCFTA preferential rate vs MFN for an HS code and trade lane.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "lookup_tariff_preference",
        "Look up the AfCFTA preferential rate vs MFN for an HS code and trade lane.",
        (
            "integration with the AfCFTA e-Tariff Book and national schedules - requires research "
            "into data availability per state party"
        ),
    )


@mcp.tool()
async def check_rules_of_origin() -> NotImplementedOutput:
    """Return the applicable rules of origin for the product line.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_rules_of_origin",
        "Return the applicable rules of origin for the product line.",
        (
            "the product-specific rules of origin annexes - requires research; RoO for some chapters "
            "are still under negotiation"
        ),
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "lookup-afcfta-tariff-preference",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "African Continental Free Trade Area (AfCFTA) Secretariat",
        "tools_working": ["get_status"],
        "tools_stubbed": ["lookup_tariff_preference", "check_rules_of_origin"],
        "primary_sources_to_verify": [
            "AfCFTA e-Tariff Book (https://au-afcfta.org)",
            "national customs schedules",
        ],
        "research_needed": (
            "Tariff phase-down schedules differ per state party and product; several rules-of-origin "
            "chapters remain under negotiation - all of it requires research against the AfCFTA "
            "e-Tariff Book rather than assumption."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
