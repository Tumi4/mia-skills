"""Tests for the MIA agent's FastAPI surface.

Same rule as test_agent.py: no test calls the real Anthropic API or needs a key.
The agent's chat() is stubbed at the service boundary so these tests exercise
routing, the rate limit, and error mapping rather than the model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import server  # noqa: E402
from agent import AgentReply, MissingAPIKeyError, TurnLimitError  # noqa: E402

client = TestClient(server.app)


@pytest.fixture(autouse=True)
def _clean_rate_limit():
    """Each test starts with a clear rate-limit window."""
    server.reset_rate_limit()
    yield
    server.reset_rate_limit()


def stub_chat(monkeypatch, result=None, raises=None):
    """Replace the agent's chat() so no model call is ever made."""

    async def _chat(session_id: str, message: str):
        if raises is not None:
            raise raises
        return result or AgentReply(reply="ok")

    monkeypatch.setattr(server.agent, "chat", _chat)


# ─── Health ─────────────────────────────────────────────────────────────────────


class TestHealth:
    def test_healthz_returns_200(self):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "mia-agent"

    def test_healthz_does_not_need_an_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["api_key_configured"] is False


# ─── The chat page ──────────────────────────────────────────────────────────────


class TestChatPage:
    """The chat page moved to /ask when the landing page took / (see test_position.py)."""

    def test_ask_renders(self):
        response = client.get("/ask")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<form" in response.text
        assert "MIA" in response.text

    def test_page_is_self_contained(self):
        """No CDN, no external assets, no localStorage - it loads on bad data."""
        html = response_text = client.get("/ask").text
        assert "<style>" in html and "<script>" in html
        assert "localStorage" not in html
        for marker in ("cdn.", "https://unpkg", "https://cdnjs", "googleapis"):
            assert marker not in response_text

    def test_page_posts_to_the_channel_agnostic_seam(self):
        assert "'/chat'" in client.get("/ask").text


# ─── /chat ──────────────────────────────────────────────────────────────────────


class TestChat:
    def test_returns_the_three_contract_fields(self, monkeypatch):
        stub_chat(
            monkeypatch,
            AgentReply(
                reply="Turnover tax is R4,500.",
                tools_called=["turnover_calculate_turnover_tax"],
                requires_human=["Confirm with a registered tax practitioner"],
            ),
        )
        response = client.post("/chat", json={"session_id": "s1", "message": "R1m turnover?"})
        assert response.status_code == 200
        body = response.json()
        assert body["reply"] == "Turnover tax is R4,500."
        assert body["tools_called"] == ["turnover_calculate_turnover_tax"]
        assert body["requires_human"] == ["Confirm with a registered tax practitioner"]

    def test_rejects_an_empty_message(self):
        response = client.post("/chat", json={"session_id": "s1", "message": ""})
        assert response.status_code == 422

    def test_rejects_a_missing_session_id(self):
        response = client.post("/chat", json={"message": "hi"})
        assert response.status_code == 422

    def test_missing_api_key_is_a_clean_503_not_a_stack_trace(self, monkeypatch):
        stub_chat(monkeypatch, raises=MissingAPIKeyError("ANTHROPIC_API_KEY is not set."))
        response = client.post("/chat", json={"session_id": "s1", "message": "hi"})
        assert response.status_code == 503
        body = response.json()
        assert body["error"] == "missing_api_key"
        assert "ANTHROPIC_API_KEY" in body["detail"]
        assert "Traceback" not in body["detail"]

    def test_turn_limit_maps_to_429(self, monkeypatch):
        stub_chat(monkeypatch, raises=TurnLimitError("This conversation hit its 20-turn limit."))
        response = client.post("/chat", json={"session_id": "s1", "message": "hi"})
        assert response.status_code == 429
        assert response.json()["error"] == "turn_limit_reached"

    def test_unexpected_failure_is_a_clean_502(self, monkeypatch):
        stub_chat(monkeypatch, raises=RuntimeError("upstream exploded"))
        response = client.post("/chat", json={"session_id": "s1", "message": "hi"})
        assert response.status_code == 502
        body = response.json()
        assert body["error"] == "upstream_error"
        assert "upstream exploded" not in body["detail"]  # internals stay internal
        assert "Traceback" not in body["detail"]


# ─── Rate limit ─────────────────────────────────────────────────────────────────


class TestRateLimit:
    def test_limit_trips_after_the_configured_number_of_requests(self, monkeypatch):
        stub_chat(monkeypatch)
        limit = server.RATE_LIMIT_REQUESTS

        for _ in range(limit):
            ok = client.post("/chat", json={"session_id": "rl", "message": "hi"})
            assert ok.status_code == 200

        blocked = client.post("/chat", json={"session_id": "rl", "message": "hi"})
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "rate_limited"

    def test_limit_is_per_session(self, monkeypatch):
        stub_chat(monkeypatch)
        for _ in range(server.RATE_LIMIT_REQUESTS):
            client.post("/chat", json={"session_id": "busy", "message": "hi"})

        assert client.post("/chat", json={"session_id": "busy", "message": "hi"}).status_code == 429
        assert client.post("/chat", json={"session_id": "quiet", "message": "hi"}).status_code == 200

    def test_window_expires(self):
        """Old hits fall out of the window, so a session recovers."""
        server.reset_rate_limit()
        for i in range(server.RATE_LIMIT_REQUESTS):
            assert server.rate_limited("w", now=1000.0 + i) is False
        assert server.rate_limited("w", now=1000.0) is True
        # far enough in the future that every earlier hit has aged out
        later = 1000.0 + server.RATE_LIMIT_WINDOW_SECONDS + 1
        assert server.rate_limited("w", now=later) is False
