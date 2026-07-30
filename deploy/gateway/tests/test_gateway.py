"""Tests for the MIA skills gateway.

The gateway is a deployment artifact: it composes the LIVE skills into one MCP
endpoint and must never leak scaffolds. These tests pin that contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastmcp import Client

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import LIVE_SKILLS, gateway  # noqa: E402

EXPECTED_NAMESPACES = {alias for _, alias in LIVE_SKILLS}


class TestGatewayContract:
    async def test_all_seven_live_skills_mounted(self):
        """Every live skill answers its namespaced get_status through the gateway."""
        assert len(LIVE_SKILLS) == 7
        async with Client(gateway) as client:
            tools = {t.name for t in await client.list_tools()}
            for alias in EXPECTED_NAMESPACES:
                assert f"{alias}_get_status" in tools

    async def test_tool_count_covers_live_library(self):
        async with Client(gateway) as client:
            tools = await client.list_tools()
            assert len(tools) >= 27  # 26 skill tools + gateway_status

    async def test_no_scaffold_tools_leak(self):
        """Hosted surface = live skills only: every tool belongs to a live
        namespace (or is the gateway's own status tool)."""
        async with Client(gateway) as client:
            for t in await client.list_tools():
                assert t.name == "gateway_status" or any(
                    t.name.startswith(f"{alias}_") for alias in EXPECTED_NAMESPACES
                ), f"unexpected tool on hosted surface: {t.name}"

    async def test_end_to_end_call_through_gateway(self):
        """R1m turnover through the gateway -> R4,500 (2027 table)."""
        async with Client(gateway) as client:
            result = await client.call_tool(
                "turnover_calculate_turnover_tax",
                {"input": {"annual_turnover_zar": 1_000_000}},
            )
            assert result.data.turnover_tax_zar == 4_500.0

    async def test_gateway_status_reports_the_mounts(self):
        async with Client(gateway) as client:
            result = await client.call_tool("gateway_status", {})
            mounted = result.data["live_skills_mounted"]
            assert len(mounted) == 7
            assert result.data["scaffolds_mounted"] == []
