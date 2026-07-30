"""
MIA Skills Gateway - one remote MCP endpoint serving every LIVE skill.

This is a DEPLOYMENT artifact, not a skill. The one-skill-one-server principle
holds: each skill in skills/ stays standalone and independently runnable. This
gateway composes the live ones into a single hosted MCP endpoint so that anyone
- starting with Michael - can point Claude (or any MCP client) at ONE URL and
call the whole live library with zero local setup.

Mounted skills (each under its own namespace so tool names cannot collide):

    s12b       calculate-section-12b-solar-deduction
    turnover   calculate-turnover-tax-south-africa
    vat        check-vat-registration-south-africa
    paye       calculate-paye-south-africa
    sdl        calculate-sdl-south-africa
    carbon     calculate-carbon-tax-south-africa
    provtax    calculate-provisional-tax-south-africa

Scaffold skills are deliberately NOT mounted - the hosted surface only exposes
what actually works.

Run locally:
    pip install -r requirements.txt
    python server.py            # serves http://localhost:8000/mcp

Deploy (Render): see deploy/gateway/README.md - render.yaml at the repo root
defines the service; Render injects PORT.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger("mia.gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# (directory, namespace) - namespaces keep tool names short but collision-free.
LIVE_SKILLS: list[tuple[str, str]] = [
    ("calculate-section-12b-solar-deduction", "s12b"),
    ("calculate-turnover-tax-south-africa", "turnover"),
    ("check-vat-registration-south-africa", "vat"),
    ("calculate-paye-south-africa", "paye"),
    ("calculate-sdl-south-africa", "sdl"),
    ("calculate-carbon-tax-south-africa", "carbon"),
    ("calculate-provisional-tax-south-africa", "provtax"),
]

gateway = FastMCP(
    "mia-skills-live",
    instructions=(
        "MIA - Made in Africa: the live, tested slice of the open-source "
        "Africa-first skills library (mia-skills). Every constant in these tools "
        "is verified against a primary source (SARS / National Treasury) with the "
        "URL and check date cited in each skill's source. Tools are namespaced by "
        "skill (s12b_*, turnover_*, vat_*, paye_*, sdl_*, carbon_*, provtax_*). "
        "Each skill's get_status tool reports its rule basis and last rule check. "
        "These are calculation tools, not tax advice - outputs flag requires_human "
        "steps honestly."
    ),
)


def _load_skill_server(directory: str, alias: str) -> FastMCP:
    """Load skills/<directory>/server.py as a uniquely named module, return its mcp."""
    path = SKILLS_DIR / directory / "server.py"
    spec = importlib.util.spec_from_file_location(f"mia_skill_{alias}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load skill from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.mcp


def build_gateway() -> FastMCP:
    """Mount every live skill under its namespace. Idempotent per process."""
    for directory, alias in LIVE_SKILLS:
        sub = _load_skill_server(directory, alias)
        gateway.mount(sub, namespace=alias)
        logger.info("mounted %s as %s_*", directory, alias)
    return gateway


build_gateway()


@gateway.tool()
async def gateway_status() -> dict:
    """What this gateway serves: the live skills, their namespaces, and the honesty rules."""
    return {
        "gateway": "mia-skills-live",
        "library": "https://github.com/aquariusfoundation/mia-skills",
        "live_skills_mounted": [{"skill": directory, "namespace": alias} for directory, alias in LIVE_SKILLS],
        "scaffolds_mounted": [],
        "principles": [
            "Every constant verified against a primary source, cited with URL + date",
            "requires_human steps flagged honestly - these are tools, not advice",
            "Scaffolds are never exposed on the hosted surface",
        ],
        "call_pattern": "<namespace>_<tool>, e.g. turnover_calculate_turnover_tax; "
        "each skill also exposes <namespace>_get_status",
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info("starting MIA skills gateway on 0.0.0.0:%s", port)
    gateway.run(transport="http", host="0.0.0.0", port=port)
