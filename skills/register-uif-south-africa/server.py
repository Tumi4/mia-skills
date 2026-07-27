"""
MIA Skill: Register an employer (and employees) for UIF with the Department of Employment and Labour.

STATUS: SCAFFOLD (v0.1.0). Tool signatures are stable; every tool below is a stub
that returns a structured not-implemented response. Nothing here pretends to work.

What this skill WILL do once implemented:
    Walk a new employer through UIF registration: determine the obligation, prepare the
    registration on u-Filing, and register employees - the sibling obligation to the
    SARS-collected contributions computed by calculate-paye-south-africa.

Primary sources to verify against when implementing (no figure or rule may be
coded without checking these live):
- u-Filing (https://ufiling.labour.gov.za)
- Department of Employment and Labour UIF pages

RESEARCH NOTES (honest gaps, not guesses):
    Registration forms (e.g. UI-8/UI-19), employee-hours thresholds and domestic-
    employer rules require research against the Department of Employment and Labour's
    current pages.

Usage (runs today, exposes stubs + get_status):
    python server.py
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from pydantic import BaseModel

logger = logging.getLogger("mia.register.uif")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

mcp = FastMCP("mia-register-uif-south-africa")


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
            "u-Filing account activation currently involves identity verification steps",
        ],
        what_this_will_do=will_do,
        needs_before_implementation=needs,
        notes=(
            f"NOT IMPLEMENTED - '{tool}' is a scaffold stub in the register-uif-south-africa "
            "skill. No real lookup or filing occurred. See get_status for the roadmap."
        ),
    )


@mcp.tool()
async def check_registration_obligation() -> NotImplementedOutput:
    """Determine whether an employer must register for UIF.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "check_registration_obligation",
        "Determine whether an employer must register for UIF.",
        ("the obligation tests (hours thresholds, domestic-worker rules) - verify on the Department's pages"),
    )


@mcp.tool()
async def prepare_registration() -> NotImplementedOutput:
    """Prepare the employer UIF registration for u-Filing.

    Implementation status: STUB - see get_status for what implementation needs.
    """
    return _stub(
        "prepare_registration",
        "Prepare the employer UIF registration for u-Filing.",
        "u-Filing automation (Playwright) and the UI-8/UI-19 document set - verify current forms",
    )


@mcp.tool()
async def get_status() -> dict:
    """Get implementation status of this skill - honest scaffold report."""
    return {
        "skill": "register-uif-south-africa",
        "version": "0.1.0",
        "status": "scaffold",
        "regulator": "Department of Employment and Labour (u-Filing)",
        "tools_working": ["get_status"],
        "tools_stubbed": ["check_registration_obligation", "prepare_registration"],
        "primary_sources_to_verify": [
            "u-Filing (https://ufiling.labour.gov.za)",
            "Department of Employment and Labour UIF pages",
        ],
        "research_needed": (
            "Registration forms (e.g. UI-8/UI-19), employee-hours thresholds and domestic-employer "
            "rules require research against the Department of Employment and Labour's current pages."
        ),
        "disclaimer": (
            "Scaffold only. Every substantive tool returns a structured "
            "not-implemented response. No regulatory figures are encoded."
        ),
    }


if __name__ == "__main__":
    mcp.run()
