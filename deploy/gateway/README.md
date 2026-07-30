# MIA Skills Gateway

One hosted MCP endpoint serving **every live skill** in mia-skills. Point Claude (or any MCP client) at a single URL and call the whole live library — no Python, no clone, no config beyond the URL.

This is a **deployment artifact, not a skill**: each skill stays standalone under `skills/`; the gateway composes the live ones under namespaces (`s12b_*`, `turnover_*`, `vat_*`, `paye_*`, `sdl_*`, `carbon_*`, `provtax_*`). Scaffolds are never mounted — the hosted surface only exposes what actually works.

---

## Run it locally

```bash
cd deploy/gateway
pip install -r requirements.txt
python server.py
# serves http://localhost:8000/mcp
```

Quick check from another terminal (Python):

```python
from fastmcp import Client
import asyncio

async def main():
    async with Client("http://localhost:8000/mcp") as c:
        print([t.name for t in await c.list_tools()])

asyncio.run(main())
```

## Deploy on Render (one time, ~10 minutes)

1. Log in at https://render.com (free tier is fine for a demo).
2. **New → Web Service**, connect the GitHub account that can see this repo, pick `mia-skills`.
3. Render reads `render.yaml` at the repo root — accept the `mia-skills-gateway` service it proposes (build: `pip install -r deploy/gateway/requirements.txt`, start: `python deploy/gateway/server.py`).
4. Deploy. Your endpoint is `https://<service-name>.onrender.com/mcp`.

Notes: the free tier sleeps after idle — first call after a quiet period takes ~30–60s to wake. Auto-deploy is on, so every push to `main` ships the latest live skills.

## Connect Claude to it

**claude.ai / Claude Desktop (custom connector):** Settings → Connectors → *Add custom connector* → paste `https://<service-name>.onrender.com/mcp`. Then ask Claude: *"Use turnover_calculate_turnover_tax to price R1.4m of turnover under the micro-business regime."*

**Any other MCP client** (Cursor, custom agents): same URL, streamable HTTP transport.

## Security posture (deliberate for v0)

- Read-only calculators: no credentials, no state, no filings — the worst an abuser can do is arithmetic.
- No auth on the endpoint yet. If usage grows beyond demos, add an auth layer before exposing anything stateful.
- Never mount a skill here that requires credentials or performs real filings without adding auth first.

## Tests

```bash
cd deploy/gateway
pytest tests -q   # contract: 7 live skills mounted, no scaffold leakage, end-to-end call
```
