"""Structural tests for the calculate-carbon-tax-south-africa scaffold.

CLAUDE.md: even scaffolds need at least one passing structural test. These pin
the scaffold's honesty: stubs must say they are stubs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import check_liability, get_status  # noqa: E402


class TestScaffoldHonesty:
    async def test_get_status_reports_scaffold(self):
        s = await get_status()
        assert s["skill"] == "calculate-carbon-tax-south-africa"
        assert s["status"] == "scaffold"
        assert len(s["tools_stubbed"]) > 0
        assert "get_status" in s["tools_working"]

    async def test_stub_returns_structured_not_implemented(self):
        out = await check_liability()
        assert out.success is False
        assert out.implemented is False
        assert out.skill_status == "scaffold"
        assert "NOT IMPLEMENTED" in out.notes

    async def test_research_gaps_disclosed_not_guessed(self):
        s = await get_status()
        assert "research" in s["research_needed"].lower()


def test_mcp_server_starts():
    from server import mcp

    assert mcp is not None
    assert mcp.name == "mia-calculate-carbon-tax-south-africa"
