"""
MIA agent service - FastAPI surface over the channel-agnostic agent core.

Surfaces:

    GET  /             the landing page - a live turnover-tax + VAT instrument
    GET  /ask          a self-contained browser chat page (inline CSS/JS, no CDN)
    POST /chat         {session_id, message} -> {reply, tools_called[], requires_human[]}
    GET  /api/position ?turnover= -> both columns, computed by the real skills
    GET  /healthz      uptime check

POST /chat is the seam every future channel adapter uses. GET /api/position is a
separate, deliberately model-free seam: the landing page must stay instant and
free to serve, so it calls the skills directly through the gateway and never
touches Anthropic. That is why it has no rate limit and no API key requirement.

A WhatsApp webhook or a Slack event handler becomes a thin translator into
POST /chat - see the "Adding a channel" section of deploy/agent/README.md.
Nothing channel-specific belongs in agent.py.

Run locally:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python server.py            # serves http://localhost:8001

Deploy (Render): a SECOND web service alongside the gateway - render.yaml at the
repo root defines both; Render injects PORT.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from pathlib import Path

from agent import (
    AgentError,
    MiaAgent,
    MissingAPIKeyError,
    TurnLimitError,
    _result_payload,
    human_items,
)
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastmcp import Client
from pydantic import BaseModel, Field

logger = logging.getLogger("mia.agent.server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer - using default %s", name, raw, default)
        return default


# Rate limit: this endpoint costs real money per call, so it is on by default.
RATE_LIMIT_REQUESTS = _env_int("MIA_RATE_LIMIT_REQUESTS", 10)
RATE_LIMIT_WINDOW_SECONDS = _env_int("MIA_RATE_LIMIT_WINDOW_SECONDS", 60)

app = FastAPI(
    title="MIA agent",
    description="Channel-agnostic MIA agent over the live mia-skills gateway.",
    version="0.1.0",
)

agent = MiaAgent()

STATIC_DIR = Path(__file__).resolve().parent / "static"
LANDING_PAGE = STATIC_DIR / "index.html"

# The landing page shares the agent's gateway so both surfaces answer from the
# same in-process skills. Reused rather than re-imported: loading the gateway
# executes seven skill modules, and doing that twice per process is waste.
_position_gateway = agent._gateway

# session_id -> timestamps of recent requests. In-memory and per-process, which
# is the right scope for a single Render web service; move to Redis before
# running more than one instance.
_hits: dict[str, deque[float]] = {}


def rate_limited(session_id: str, now: float | None = None) -> bool:
    """Record a request and report whether this session is over its limit."""
    now = time.monotonic() if now is None else now
    window = _hits.setdefault(session_id, deque())
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= RATE_LIMIT_REQUESTS:
        return True
    window.append(now)
    return False


def reset_rate_limit() -> None:
    """Clear all rate-limit state (used by tests)."""
    _hits.clear()


# ─── Models ─────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    tools_called: list[str] = []
    requires_human: list[str] = []


# ─── Routes ─────────────────────────────────────────────────────────────────────


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer one message. The channel-agnostic seam every adapter calls.

    Errors are returned as clean JSON, never a stack trace:
      429 rate limited        - too many messages from this session
      429 turn limit reached  - session hit its per-session cap
      503 missing API key     - ANTHROPIC_API_KEY is not set on the server
      502 upstream failure    - the model call itself failed
    """
    if rate_limited(request.session_id):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "detail": (
                    f"Too many messages - the limit is {RATE_LIMIT_REQUESTS} per "
                    f"{RATE_LIMIT_WINDOW_SECONDS}s. Give it a moment and try again."
                ),
            },
        )

    try:
        result = await agent.chat(request.session_id, request.message)
    except MissingAPIKeyError as exc:
        logger.error("chat failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"error": "missing_api_key", "detail": str(exc)},
        )
    except TurnLimitError as exc:
        return JSONResponse(
            status_code=429,
            content={"error": "turn_limit_reached", "detail": str(exc)},
        )
    except AgentError as exc:
        logger.error("chat failed: %s", exc)
        return JSONResponse(status_code=502, content={"error": "agent_error", "detail": str(exc)})
    except Exception as exc:  # never leak a stack trace to a founder's phone
        logger.exception("unexpected failure answering a chat turn")
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "detail": f"The assistant could not answer that just now ({type(exc).__name__}).",
            },
        )

    return ChatResponse(
        reply=result.reply,
        tools_called=result.tools_called,
        requires_human=result.requires_human,
    )


def _zar(value: float) -> str:
    """Rand, grouped the South African way: R1 400 000, not R1,400,000.

    The page uses spaces throughout, and live and offline answers must be
    indistinguishable - a separator that changes when the network arrives would
    read as two different systems disagreeing.
    """
    return "R" + f"{value:,.0f}".replace(",", " ")


def _short_millions(value: float) -> str:
    """R2.3m / R1m - the compact form the card's verdicts use."""
    millions = value / 1_000_000
    text = f"{millions:.1f}".rstrip("0").rstrip(".")
    return f"R{text}m"


def _vat_now(vat: dict) -> dict:
    """The VAT column as the live skill reported it."""
    kind = vat.get("registration_type")
    mandatory = vat.get("mandatory_threshold_zar") or 0
    voluntary = vat.get("voluntary_minimum_zar") or 0
    if kind == "mandatory":
        status = "Compulsory"
        note = (
            f"Over {_short_millions(mandatory)} — register within "
            f"{vat.get('registration_deadline_business_days', 21)} business days"
        )
    elif kind == "voluntary_available":
        status = "Voluntary"
        note = f"Above {_zar(voluntary)}, below the {_short_millions(mandatory)} compulsory threshold"
    else:
        status = "Not yet"
        note = f"Under {_zar(voluntary)} — other routes may still apply"
    return {"vat_status": status, "vat_note": note}


def _vat_then(turnover: float, status: dict) -> dict:
    """The VAT column as the superseded thresholds would have decided it.

    Reconstructed rather than computed by the skill: the skill only implements
    current law, which is correct - it should not offer to answer as if the old
    rules still applied. The superseded figures come from the skill's own
    get_status output, so this stays traceable to one source of truth.
    """
    mandatory = status.get("previous_mandatory_threshold_zar")
    voluntary = status.get("previous_voluntary_minimum_zar")
    days = status.get("registration_deadline_business_days")
    if mandatory is None or voluntary is None:
        # The skill stopped publishing the old thresholds; say so rather than guess.
        return {"vat_status": None, "vat_note": "Superseded thresholds unavailable."}

    if turnover > mandatory:
        return {
            "vat_status": "Compulsory",
            "vat_note": (f"Old {_short_millions(mandatory)} threshold — {days} business days to register"),
        }
    if turnover > voluntary:
        return {"vat_status": "Voluntary", "vat_note": f"Old {_zar(voluntary)} voluntary minimum"}
    return {"vat_status": "Not yet", "vat_note": f"Under the old {_zar(voluntary)} minimum"}


@app.get("/api/position")
async def position(
    turnover: float = Query(..., ge=0, le=1_000_000_000, description="Annual turnover in rand"),
):
    """Both columns of the landing page's comparison, computed by the real skills.

    The page ships with generated constants so it works before this responds (and
    with JS off, and if this fails). This endpoint is what makes the served page
    honest: the figures come from the same code the MCP tools run, not from a
    copy of the rules that could drift.

    Deliberately model-free - no Anthropic call, no API key, no rate limit. It is
    a pure calculation and must stay free to serve.
    """
    try:
        async with Client(_position_gateway) as mcp:
            now_tax = _result_payload(
                await mcp.call_tool(
                    "turnover_calculate_turnover_tax",
                    {"input": {"annual_turnover_zar": turnover, "tax_year": 2027}},
                )
            )
            then_tax = _result_payload(
                await mcp.call_tool(
                    "turnover_calculate_turnover_tax",
                    {"input": {"annual_turnover_zar": turnover, "tax_year": 2026}},
                )
            )
            vat = _result_payload(
                await mcp.call_tool(
                    "vat_check_registration_required",
                    {"input": {"rolling_12m_taxable_supplies_zar": turnover}},
                )
            )
            vat_status = _result_payload(await mcp.call_tool("vat_get_status", {}))
    except Exception as exc:
        # The page falls back to its generated constants on any non-200, so this
        # degrades to "the offline answer" rather than to a blank card.
        logger.exception("position lookup failed for turnover=%s", turnover)
        return JSONResponse(
            status_code=502,
            content={
                "error": "calculation_failed",
                "detail": f"Could not compute that position just now ({type(exc).__name__}).",
            },
        )

    human = sorted(set(human_items(now_tax) + human_items(vat)))

    return {
        "turnover_zar": turnover,
        "now": {
            "basis": "Current law - 2027 year of assessment",
            "turnover_tax_zar": now_tax.get("turnover_tax_zar"),
            "band_applied": now_tax.get("band_applied"),
            "qualifies": not now_tax.get("exceeds_qualifying_limit"),
            "qualifying_limit_zar": now_tax.get("qualifying_limit_zar"),
            **_vat_now(vat),
        },
        "then": {
            "basis": "Superseded - rules before 1 April 2026",
            "turnover_tax_zar": then_tax.get("turnover_tax_zar"),
            "band_applied": then_tax.get("band_applied"),
            "qualifies": not then_tax.get("exceeds_qualifying_limit"),
            "qualifying_limit_zar": then_tax.get("qualifying_limit_zar"),
            **_vat_then(turnover, vat_status),
        },
        "requires_human": human,
        "computed_by": "mia-skills (live)",
        "disclaimer": "This is a calculation, not tax advice.",
    }


@app.get("/healthz")
async def healthz():
    """Uptime check. Deliberately does not touch the model - it must stay free."""
    return {
        "status": "ok",
        "service": "mia-agent",
        "model": agent.model,
        "api_key_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


# ─── Browser chat page ──────────────────────────────────────────────────────────
#
# Self-contained on purpose: inline CSS and JS, no CDN, no build step, no
# localStorage. It will be opened on mid-range Android phones over patchy data,
# so it stays plain and small. The session id lives in a JS variable for the
# life of the tab - reload and you get a fresh conversation.

CHAT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIA - South African business tax calculations</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f6f7f9; color: #16191d; display: flex; flex-direction: column;
    height: 100vh; height: 100dvh;
  }
  header {
    background: #14532d; color: #fff; padding: 12px 16px; flex-shrink: 0;
  }
  header h1 { margin: 0; font-size: 17px; font-weight: 600; }
  header p { margin: 2px 0 0; font-size: 12px; opacity: .85; }
  #log { flex: 1; overflow-y: auto; padding: 16px; }
  .msg { max-width: 90%; margin-bottom: 14px; padding: 10px 13px; border-radius: 12px;
         line-height: 1.45; font-size: 15px; white-space: pre-wrap; word-wrap: break-word; }
  .user { background: #14532d; color: #fff; margin-left: auto; border-bottom-right-radius: 3px; }
  .mia  { background: #fff; border: 1px solid #e2e5ea; border-bottom-left-radius: 3px; }
  .err  { background: #fdecec; border: 1px solid #f3c0c0; color: #8a1c1c; }
  .meta { font-size: 12px; color: #5b6470; margin: -8px 0 14px 2px; }
  .human { background: #fff8e6; border: 1px solid #f0dca8; border-radius: 10px;
           padding: 10px 13px; margin: -8px 0 14px; font-size: 13.5px; }
  .human strong { display: block; margin-bottom: 5px; }
  .human ul { margin: 0; padding-left: 18px; }
  .human li { margin-bottom: 3px; }
  form { display: flex; gap: 8px; padding: 10px; background: #fff;
         border-top: 1px solid #e2e5ea; flex-shrink: 0; }
  input {
    flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ccd2da;
    border-radius: 10px; min-width: 0;
  }
  input:focus { outline: 2px solid #14532d; outline-offset: -1px; }
  button {
    padding: 12px 18px; font-size: 15px; font-weight: 600; background: #14532d;
    color: #fff; border: 0; border-radius: 10px; cursor: pointer;
  }
  button:disabled { opacity: .5; cursor: default; }
  .hint { padding: 0 16px 12px; font-size: 12.5px; color: #5b6470; }
  .hint button {
    background: #fff; color: #14532d; border: 1px solid #cfd6dd; font-weight: 500;
    padding: 7px 11px; border-radius: 999px; font-size: 12.5px; margin: 4px 4px 0 0;
  }
</style>
</head>
<body>
<header>
  <h1>MIA</h1>
  <p>South African business tax, payroll &amp; compliance calculations</p>
</header>

<div id="log">
  <div class="msg mia">Hi. I run South African business tax, payroll and compliance calculations
- turnover tax, VAT registration, PAYE, SDL, carbon tax, provisional tax, and the Section 12B
solar deduction.

Every number I give comes from a verified calculation, not from memory. These are calculations,
not tax advice - always have a registered tax practitioner confirm before you file.</div>
  <div class="hint">
    <button type="button" class="ex">What turnover tax would I pay on R1.4m of turnover?</button>
    <button type="button" class="ex">Do I have to register for VAT at R1.2m turnover?</button>
    <button type="button" class="ex">PAYE on a R30,000 monthly salary, age 40</button>
  </div>
</div>

<form id="f">
  <input id="m" autocomplete="off" placeholder="Ask about a tax calculation..." required>
  <button id="b" type="submit">Send</button>
</form>

<script>
  var sessionId = 'web-' + Math.random().toString(36).slice(2) + '-' + Date.now();
  var log = document.getElementById('log');
  var form = document.getElementById('f');
  var input = document.getElementById('m');
  var button = document.getElementById('b');

  function el(cls, text) {
    var d = document.createElement('div');
    d.className = cls;
    d.textContent = text;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }

  function humanBlock(items) {
    var d = document.createElement('div');
    d.className = 'human';
    var s = document.createElement('strong');
    s.textContent = 'Human steps required';
    d.appendChild(s);
    var ul = document.createElement('ul');
    items.forEach(function (i) {
      var li = document.createElement('li');
      li.textContent = i;
      ul.appendChild(li);
    });
    d.appendChild(ul);
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }

  document.querySelectorAll('.ex').forEach(function (b) {
    b.addEventListener('click', function () {
      input.value = b.textContent;
      form.dispatchEvent(new Event('submit', { cancelable: true }));
    });
  });

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;

    el('msg user', text);
    input.value = '';
    input.disabled = true;
    button.disabled = true;
    var pending = el('msg mia', 'Working on it...');

    try {
      var res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text })
      });
      var data = await res.json();
      if (!res.ok) {
        pending.className = 'msg err';
        pending.textContent = data.detail || 'Something went wrong. Try again shortly.';
      } else {
        pending.textContent = data.reply || '(no reply)';
        if (data.tools_called && data.tools_called.length) {
          el('meta', 'Calculated with: ' + data.tools_called.join(', '));
        }
        if (data.requires_human && data.requires_human.length) {
          humanBlock(data.requires_human);
        }
      }
    } catch (err) {
      pending.className = 'msg err';
      pending.textContent = 'Could not reach the assistant. Check your connection and try again.';
    } finally {
      input.disabled = false;
      button.disabled = false;
      input.focus();
    }
  });
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """The landing page - a live turnover-tax and VAT instrument.

    Read from disk per request rather than cached at import so that editing the
    page during local development does not need a restart. The file is ~37KB;
    on Render it is served from the container's own filesystem.

    If the file is missing (a partial deploy, a bad build), fall back to the chat
    page rather than 500 - a working chat surface beats an error page.
    """
    try:
        return HTMLResponse(content=LANDING_PAGE.read_text(encoding="utf-8"))
    except OSError:
        logger.exception("landing page missing at %s - serving the chat page instead", LANDING_PAGE)
        return HTMLResponse(content=CHAT_PAGE)


@app.get("/ask", response_class=HTMLResponse)
async def ask():
    """The browser chat page - where a founder asks in their own words."""
    return HTMLResponse(content=CHAT_PAGE)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    logger.info("starting MIA agent on 0.0.0.0:%s (model=%s)", port, agent.model)
    uvicorn.run(app, host="0.0.0.0", port=port)
