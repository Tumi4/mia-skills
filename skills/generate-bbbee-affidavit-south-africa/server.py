"""
MIA Skill: Generate a B-BBEE sworn affidavit for an Exempted Micro Enterprise (EME) or qualifying start-up.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Determine whether a business qualifies for the EME sworn-affidavit route instead of
    a paid verification certificate, and generate the affidavit from the official dtic
    template ready for commissioning.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- the dtic B-BBEE pages and official affidavit templates (https://www.thedtic.gov.za)

RESEARCH NOTES (honest gaps, not guesses):
    The EME turnover threshold, start-up recognition rules and current official
    affidavit templates require research against the live dtic codes of good practice.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.generate.bbbee.affidavit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-generate-bbbee-affidavit-south-africa")


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
            "The affidavit must be sworn before a Commissioner of Oaths - always a human step",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the generate-bbbee-affidavit-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_eme_qualification() -> NotImplementedOutput:
    """Check whether the business qualifies as an EME (affidavit route).

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_eme_qualification",
        "Check whether the business qualifies as an EME (affidavit route).",
        (
            "the current EME turnover threshold and black-ownership level mapping - requires research "
            "on the live dtic codes; do not assume the commonly quoted R10m figure"
        ),
    )


@mcp.tool()
async def generate_affidavit() -> NotImplementedOutput:
    """Generate the sworn-affidavit document from the official dtic template.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "generate_affidavit",
        "Generate the sworn-affidavit document from the official dtic template.",
        "template retrieval and field-filling from the official dtic affidavit forms",
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "generate-bbbee-affidavit-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Department of Trade, Industry and Competition (the dtic)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_eme_qualification", "generate_affidavit"],
        "primary_sources_to_verify": [
            "the dtic B-BBEE pages and official affidavit templates (https://www.thedtic.gov.za)",
        ],
        "research_needed": (
            "The EME turnover threshold, start-up recognition rules and current official affidavit "
            "templates require research against the live dtic codes of good practice."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
