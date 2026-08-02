# MIA agent service

A **channel-agnostic MIA agent** — an LLM wired to the live mia-skills gateway — with a browser chat page as its first surface. WhatsApp and Slack become thin adapters later.

This is a **deployment artifact, not a skill.** Each skill stays standalone under `skills/`; the [gateway](../gateway/README.md) composes the live ones into one MCP surface; this service puts a conversation in front of that surface.

---

## What it is

```
   browser chat page  ─┐
   WhatsApp adapter   ─┤──▶  POST /chat  ──▶  agent.py  ──▶  gateway (in-process)  ──▶  live skills
   Slack adapter      ─┘     (the seam)      (no web fw)      no network hop
```

Two files, one seam:

- **`agent.py`** — the core. No web framework, no HTTP, nothing channel-specific. It imports the gateway **in-process** and drives it with `fastmcp.Client(gateway)` — same repo, same process, so there is no network hop and no dependency on the deployed gateway being up. It lists the gateway's tools, converts them to Anthropic tool schemas, and runs a proper tool-use loop (the model may call several tools before answering).
- **`server.py`** — FastAPI. `GET /` serves the landing page; `GET /ask` is the browser chat page; `POST /chat` is the channel-agnostic seam; `GET /api/position` computes the landing page's two columns through the real skills (no model call, no API key, no rate limit); `GET /healthz` is for uptime checks.
- **`static/index.html`** — the landing page. Its JS constants are generated from the Python skills by `scripts/gen_web_constants.py` and guarded in CI; never hand-edit between the `MIA:GENERATED-CONSTANTS` sentinels.

### The system prompt is the product

It lives in one clearly-marked constant (`SYSTEM_PROMPT` in `agent.py`) and enforces four rules:

1. **Narrowly scoped** to South African business tax, payroll and compliance calculations via these tools. Anything else gets a polite decline plus what MIA *does* cover. This is deliberate, not fussiness: Meta's 2026 WhatsApp policy permits task-scoped business assistants but bans general-purpose LLM chatbots — a "MIA can chat about anything" bot would get a WhatsApp number banned once that adapter ships.
2. **Never state a rand figure, rate or threshold from model knowledge.** Every number must come from a tool call. If no tool covers it, MIA says so rather than estimating. The tools are verified against SARS / National Treasury with a cited URL and check date; training data is not.
3. **`requires_human` / `human_steps` / `warnings` are passed to the user, never summarised away.** This is the honesty contract in [`docs/integration.md`](../../docs/integration.md). `/chat` also returns them as a structured `requires_human[]` array, so an adapter can render them even if the prose ever dropped one.
4. **Always a calculation, never tax advice.**

---

## Run it locally

```bash
cd deploy/agent
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python server.py                       # serves http://localhost:8001
```

Open <http://localhost:8001> and ask *"What turnover tax would I pay on R1.4m of turnover?"*

The key is read **from the environment only** and is never written to any file. `.env` and `.env.local` are gitignored at the repo root — if you keep the key in `deploy/agent/.env`, it stays out of git.

### Environment variables

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Model credentials. Env only, never written to disk. |
| `MIA_MODEL` | `claude-opus-5` | Model id. **Model ids change** — this is deliberately env-driven and defined in exactly one place near the top of `agent.py`, rather than hardcoded deep in the request call, so a model change is a config edit and not a code hunt. |
| `MIA_MAX_OUTPUT_TOKENS` | `4096` | Max output tokens per reply. |
| `MIA_MAX_TOOL_ITERATIONS` | `6` | Max model↔tool round trips in one turn. Stops a runaway loop. |
| `MIA_MAX_TURNS` | `20` | Max user turns per session. |
| `MIA_EFFORT` | `medium` | Reasoning effort: `low`/`medium`/`high`/`xhigh`/`max`. |
| `MIA_RATE_LIMIT_REQUESTS` | `10` | Requests allowed per session per window. |
| `MIA_RATE_LIMIT_WINDOW_SECONDS` | `60` | The rate-limit window. |
| `PORT` | `8001` | Injected by Render, same as the gateway. |

The last five are cost guards. **This endpoint costs real money per call** — every one of them is a spend ceiling, not a nicety.

---

## The API

### `POST /chat`

```json
{ "session_id": "web-abc123", "message": "Turnover tax on R1.4m?" }
```

```json
{
  "reply": "On R1,400,000 of turnover the tax is R20,800...",
  "tools_called": ["turnover_calculate_turnover_tax"],
  "requires_human": ["Confirm with a registered tax practitioner before filing"]
}
```

Errors come back as clean JSON, never a stack trace:

| Status | `error` | When |
|---|---|---|
| 429 | `rate_limited` | Too many messages from this session |
| 429 | `turn_limit_reached` | Session hit `MIA_MAX_TURNS` |
| 503 | `missing_api_key` | `ANTHROPIC_API_KEY` not set on the server |
| 502 | `upstream_error` | The model call failed |

### `GET /api/position` — the landing page's figures, from the real skills

```
GET /api/position?turnover=1400000
```

Returns both columns — current law and the superseded pre-April-2026 rules — computed
by the same skills the MCP tools run, plus the `requires_human` steps they flagged.

Deliberately model-free: no Anthropic call, no `ANTHROPIC_API_KEY`, no rate limit. The
landing page must stay instant and free to serve. The page ships with generated
constants so it is already correct before this responds; a slow or failed request
leaves the offline figures in place rather than blanking the card.

### `GET /ask` — the browser chat page

One self-contained HTML page: inline CSS and JS, no CDN, no build step, no `localStorage`. Plain and fast, because it will be opened by founders on mid-range phones over patchy data. The session id lives in a JS variable for the life of the tab — reload for a fresh conversation.

### `GET /healthz`

Returns `{"status": "ok", ...}` and deliberately does not touch the model, so uptime checks stay free.

---

## Deploy on Render (as a SECOND service)

The gateway and the agent are **two separate web services from the same repo**. `render.yaml` at the repo root already defines both — the gateway's entry is unchanged.

1. Push to `main`. In Render: **New → Blueprint** (or open the existing blueprint) and let it read `render.yaml`.
2. Accept the second service, `mia-agent`:
   - build: `pip install -r deploy/agent/requirements.txt`
   - start: `python deploy/agent/server.py`
3. **Set `ANTHROPIC_API_KEY`** on the `mia-agent` service under *Environment*. It is marked `sync: false` in `render.yaml`, so Render prompts for it and never stores it in the repo. The service cannot answer without it — `/chat` returns a clean 503 and `/healthz` reports `api_key_configured: false`.
4. Deploy. Your chat page is `https://mia-agent.onrender.com/`.

### The ~$7/month note

The free tier sleeps after ~15 minutes idle and takes 30–60s to wake. That is fine for the gateway (an MCP endpoint a developer pokes) and **not fine for a customer-facing chat page** — a founder who waits a minute on a blank screen leaves. For anything you send real users to, put `mia-agent` on Render's **Starter plan (~$7/month)**, which does not sleep. The gateway can stay free.

Remember the agent also costs Anthropic API tokens per message on top of hosting. The cost guards above are what keep that bounded.

---

## Adding a channel

`POST /chat` is the entire integration surface. A new channel is a translator, not a new agent — **nothing channel-specific belongs in `agent.py`**.

A WhatsApp webhook adapter would be roughly:

```python
# deploy/agent/channels/whatsapp.py  (sketch — not built yet)
from fastapi import APIRouter, Request
import httpx

router = APIRouter()
AGENT = "http://localhost:8001/chat"   # or import MiaAgent and call it directly

@router.get("/webhook/whatsapp")        # 1. Meta's one-time verification handshake
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params["hub.challenge"])
    return {"error": "bad token"}

@router.post("/webhook/whatsapp")       # 2. Inbound messages
async def inbound(request: Request):
    payload = await request.json()
    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

    # The founder's phone number IS the session id - conversation continuity for free.
    async with httpx.AsyncClient() as http:
        result = (await http.post(AGENT, json={
            "session_id": msg["from"],
            "message": msg["text"]["body"],
        })).json()

    text = result["reply"]
    if result["requires_human"]:        # honesty contract survives the channel hop
        text += "\n\nHuman steps required:\n" + "\n".join(
            f"- {s}" for s in result["requires_human"]
        )

    await send_whatsapp_message(to=msg["from"], text=text)
    return {"status": "ok"}
```

Four things to get right in any adapter:

1. **Map the channel's user identity to `session_id`** — phone number for WhatsApp, `channel:user` for Slack. That is what gives multi-turn continuity.
2. **Render `requires_human[]` explicitly.** The model already puts them in the prose, but a channel that reformats or truncates must not lose them.
3. **Answer the platform's verification handshake** (Meta's `hub.challenge`, Slack's `url_verification`) and verify inbound signatures.
4. **Reply inside the platform's window** — Meta wants a fast `200`. If a turn is slow, ack immediately and send the reply asynchronously.

The scope rule in the system prompt is what keeps a WhatsApp number compliant with Meta's 2026 business-assistant policy. Do not loosen it for a channel.

---

## Tests

```bash
cd deploy/agent
pytest tests -q
```

**No test calls the real Anthropic API or needs a key** — the model client is always a fake returning scripted responses. The **gateway is real**, though: tests drive the actual in-process gateway, because "the agent reaches the live skills without a network hop" is the thing worth testing. Coverage includes the multi-tool turn, `requires_human` reaching the reply, an out-of-scope decline, the rate limit tripping, `/healthz`, and tool discovery pinned against the gateway's own live tool count.

---

## Limits and honesty

- **Sessions are in-memory and per-process.** A restart clears every conversation, and the rate limit is per instance — move both to Redis before running more than one instance.
- **No auth on `/chat`.** The rate limit is the only spend guard. Add auth before advertising the URL widely.
- **The agent is only as current as the skills.** Each skill's `get_status` reports its rule basis and last rule check; if one looks stale, re-verify before relying on it.
- This is a **calculation tool, not tax advice.**

---

## Maintainer

The Aquarius Foundation · skills@theaquariusfoundation.org
