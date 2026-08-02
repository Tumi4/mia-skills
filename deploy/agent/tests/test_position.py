"""Tests for GET /api/position and the two HTML surfaces.

These run against the REAL gateway and the REAL skills - no mocks. The whole
point of the endpoint is that the landing page's figures come from the same code
the MCP tools run, so a test that mocked the skills would test nothing worth
testing. No Anthropic call is involved, so this needs no API key and costs
nothing.

The expected figures below are hand-derived from the published SARS tables, not
copied from a previous run:

    2027 turnover tax: 0% to R600,000; R3,500 + 2% above R950,000;
                       R12,500 + 3% above R1,400,000
    2026 turnover tax: 0% to R335,000; R1,650 + 2% above R500,000;
                       R6,650 + 3% above R750,000

    R1,400,000 @ 2027 -> 3,500 + 0.02 * 450,000  = 12,500
    R1,400,000 @ 2026 -> 6,650 + 0.03 * 650,000  = 26,150
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(server.app)


# ─── the figures ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("turnover", "tax_now", "tax_then"),
    [
        (0, 0.0, 0.0),
        (335_000, 0.0, 0.0),  # both still in their tax-free band
        (600_000, 0.0, 3_650.0),  # 2026: 6,650 - 3% of the 750k-600k gap
        (950_000, 3_500.0, 12_650.0),
        (1_400_000, 12_500.0, 26_150.0),  # the moment the page is built around
        (2_300_000, 39_500.0, 53_150.0),
    ],
)
def test_turnover_tax_matches_the_published_tables(client, turnover, tax_now, tax_then):
    body = client.get("/api/position", params={"turnover": turnover}).json()
    assert body["now"]["turnover_tax_zar"] == tax_now
    assert body["then"]["turnover_tax_zar"] == tax_then


@pytest.mark.parametrize(
    ("turnover", "qualifies_now", "qualifies_then"),
    [
        (1_000_000, True, True),
        (1_000_001, True, False),  # the old R1m cliff
        (2_300_000, True, False),
        (2_300_001, False, False),  # today's R2.3m cliff
    ],
)
def test_qualification_flips_at_the_right_thresholds(client, turnover, qualifies_now, qualifies_then):
    body = client.get("/api/position", params={"turnover": turnover}).json()
    assert body["now"]["qualifies"] is qualifies_now
    assert body["then"]["qualifies"] is qualifies_then


@pytest.mark.parametrize(
    ("turnover", "vat_now", "vat_then"),
    [
        (50_000, "Not yet", "Not yet"),
        (50_001, "Not yet", "Voluntary"),  # old R50k voluntary minimum
        (120_001, "Voluntary", "Voluntary"),  # today's R120k voluntary minimum
        (1_000_001, "Voluntary", "Compulsory"),  # old R1m compulsory threshold
        (2_300_001, "Compulsory", "Compulsory"),  # today's R2.3m threshold
    ],
)
def test_vat_status_flips_at_the_right_thresholds(client, turnover, vat_now, vat_then):
    body = client.get("/api/position", params={"turnover": turnover}).json()
    assert body["now"]["vat_status"] == vat_now
    assert body["then"]["vat_status"] == vat_then


def test_the_1_4m_case_is_a_different_outcome_not_a_different_amount(client):
    """The page's central claim, asserted as a contract rather than as copy."""
    body = client.get("/api/position", params={"turnover": 1_400_000}).json()
    assert body["now"]["qualifies"] is True
    assert body["then"]["qualifies"] is False
    assert body["now"]["vat_status"] != body["then"]["vat_status"]


# ─── the honesty contract ───────────────────────────────────────────────────────


def test_response_carries_the_disclaimer_and_human_steps(client):
    body = client.get("/api/position", params={"turnover": 1_400_000}).json()
    assert "not tax advice" in body["disclaimer"].lower()
    assert body["requires_human"], "the skills flag human steps; the API must pass them on"
    assert all(isinstance(item, str) and item for item in body["requires_human"])


def test_figures_are_formatted_the_south_african_way(client):
    """Live notes must read like the page's offline notes - spaces, not commas."""
    body = client.get("/api/position", params={"turnover": 1_400_000}).json()
    for note in (body["now"]["vat_note"], body["then"]["vat_note"]):
        assert "R1,000,000" not in note and "R120,000" not in note


def test_the_separator_is_an_ordinary_space():
    """The page's JS groups with U+0020; the API must not use U+00A0.

    A non-breaking space looks identical on screen but is a different character,
    so the live answer would silently differ from the offline one - the sort of
    invisible mismatch that is impossible to spot in review.
    """
    assert server._zar(1_400_000) == "R1 400 000"
    assert " " not in server._zar(1_400_000)


def test_the_then_column_is_labelled_as_superseded(client):
    body = client.get("/api/position", params={"turnover": 1_400_000}).json()
    assert "superseded" in body["then"]["basis"].lower()
    assert "current" in body["now"]["basis"].lower()


# ─── input handling ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [-1, "abc"])
def test_bad_turnover_is_rejected_cleanly(client, bad):
    assert client.get("/api/position", params={"turnover": bad}).status_code == 422


def test_turnover_is_required(client):
    assert client.get("/api/position").status_code == 422


# ─── the surfaces ───────────────────────────────────────────────────────────────


def test_root_serves_the_landing_page(client):
    body = client.get("/").text
    assert "Your tax position" in body
    assert "MIA:GENERATED-CONSTANTS:START" in body


def test_landing_page_works_without_javascript(client):
    """The served HTML must carry real figures, not empty placeholders."""
    body = client.get("/").text
    assert "<noscript>" in body
    assert "R12 500" in body and "R26 150" in body


def test_landing_page_never_softens_the_disclaimer(client):
    body = client.get("/").text.lower()
    assert body.count("not tax advice") >= 3
    assert "will not do this for you" in body


def test_ask_serves_the_chat_page(client):
    body = client.get("/ask").text
    assert "Ask about a tax calculation" in body


def test_root_falls_back_to_chat_if_the_page_is_missing(client, monkeypatch, tmp_path):
    """A partial deploy should lose the landing page, not the whole service."""
    monkeypatch.setattr(server, "LANDING_PAGE", tmp_path / "does-not-exist.html")
    response = client.get("/")
    assert response.status_code == 200
    assert "Ask about a tax calculation" in response.text


def test_position_needs_no_api_key(client, monkeypatch):
    """The landing page must stay free to serve - no model call, ever."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert client.get("/api/position", params={"turnover": 500_000}).status_code == 200
