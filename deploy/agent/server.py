"""
MIA agent service - FastAPI surface over the channel-agnostic agent core.

Two surfaces, one seam:

    POST /chat    {session_id, message} -> {reply, tools_called[], requires_human[]}
    GET  /        a self-contained browser chat page (inline CSS/JS, no CDN)
    GET  /healthz uptime check

POST /chat is the seam every future channel adapter uses. A WhatsApp webhook or
a Slack event handler becomes a thin translator into that one call - see the
"Adding a channel" section of deploy/agent/README.md. Nothing channel-specific
belongs in agent.py.

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

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from agent import AgentError, MiaAgent, MissingAPIKeyError, TurnLimitError

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
    """The browser chat page - the agent's first surface."""
    return HTMLResponse(content=CHAT_PAGE)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    logger.info("starting MIA agent on 0.0.0.0:%s (model=%s)", port, agent.model)
    uvicorn.run(app, host="0.0.0.0", port=port)
