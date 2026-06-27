# Contributing to mia-skills

Thank you for considering a contribution. This repo is the open-source moat of MIA — and every skill added makes it harder for anyone to replicate what we're building.

This guide covers: how to propose a skill, how to build one, what we expect in a PR, and the legal/ethical guardrails.

---

## Who can contribute

Anyone. African developers especially welcome. The whole point of this library is to encode knowledge that currently lives in WhatsApp groups, accelerator slack channels, and tribal memory. If you've registered a company, filed a grant, opened a bank account, navigated a regulator, or wired up M-Pesa for a client — you have skills knowledge worth sharing.

You don't need to be a senior engineer. You need to be willing to test what you write.

---

## Before you write code

Open an **issue** with the proposed skill first. Use the "New skill proposal" template. Include:

1. **Name** — `<verb>-<noun>-<jurisdiction>` format (e.g. `claim-section-12j`)
2. **Jurisdiction** — country code(s) the skill applies to
3. **Regulator(s)** — the body whose process you're wrapping
4. **What it does** — 2–3 sentences
5. **What it doesn't do** — 2–3 sentences on the limits
6. **Why it matters** — who needs this and what pain it removes
7. **Existing solutions** — what founders do today (this becomes the README's "compared to alternatives" section)

Maintainers will respond within 5 business days with one of:
- ✅ **Go ahead** — proceed to a PR
- 🟡 **Refine first** — feedback on scope/naming/architecture
- ❌ **Not yet** — reasons (usually: too broad, already in progress, or out of scope)

This proposal step saves everyone time. Don't skip it.

---

## How to build a skill

### 1. Start from the template

```bash
git clone https://github.com/aquariusfoundation/mia-skills
cd mia-skills
./scripts/new-skill.sh my-skill-name
cd skills/my-skill-name
```

This creates the standard file layout with stub `server.py`, `skill.json`, `README.md`, and `tests/`.

### 2. Define your inputs and outputs

Open `server.py` and define Pydantic models for what your skill takes in and what it returns. **Do this before writing any logic.** If the data model isn't clear, the skill isn't clear.

### 3. Implement the happy path

Wire up the actual integration — whether it's an API client, a Playwright browser automation, or a document generator. Get the happy path working end-to-end before worrying about edge cases.

### 4. Handle the unhappy paths

For every reasonable failure mode:
- API rate limits → exponential backoff with logged retries
- Network errors → typed exceptions, no silent failures
- Missing credentials → clear error message naming the env var
- Regulator-side captchas → return `requires_human=True` with instructions
- Ambiguous inputs → validate via Pydantic; reject with helpful messages

### 5. Write tests

Every skill needs:
- **At least one structural test** — proves the MCP server starts and lists tools
- **Tool-level tests** for each tool's happy path
- **Validation tests** for input edge cases
- **Where applicable, integration tests** behind a `@pytest.mark.integration` decorator (these run with real credentials and are gated in CI)

Run `pytest` in your skill directory. Green before PR.

### 6. Document it

The skill's `README.md` must cover:
- **What it does** (one paragraph)
- **What it requires** (credentials, accounts, env vars)
- **How to use it** (working example)
- **Limits** (the human steps, the rate limits, the failure modes)
- **Cost and timeline** (real-world estimates)
- **Compared to alternatives** (what founders do without this skill)
- **Maintainer contact**

If a founder reading the README can't decide whether to use the skill, the README is incomplete.

### 7. Submit a PR

PR title format: `feat(skill): add <skill-name>` or `fix(<skill-name>): <description>`

The PR description should include:
- Link to the original proposal issue
- What changed
- How you tested it
- Any open questions for review

CI must pass before review. Reviews happen within 5 business days.

---

## What we expect in code

- **Python 3.11+** — use modern features (match statements, type hints, async/await)
- **Strict typing** — `mypy --strict` should pass eventually; we're getting there
- **Pydantic v2** — for all models, not v1
- **No print statements** — use structured logging (`logging` module)
- **No bare except** — catch specific exceptions
- **No sleeping** — use proper async waits
- **No global state** — skills are stateless unless explicitly documented otherwise
- **Black/Ruff formatted** — CI enforces this; run `ruff format` before pushing

---

## Legal and ethical guardrails

This is important. Read carefully.

### What skills must NOT do

- **Submit filings without explicit user consent.** Always confirm before any irreversible action (registration submission, payment, document signing).
- **Store user credentials.** Credentials come from env vars at runtime, never persisted by skills.
- **Bypass regulatory requirements.** If a process requires a director's physical signature, the skill says so and stops. Don't engineer around legal requirements.
- **Misrepresent themselves.** If a regulator requires that an authorized agent file on behalf of a company, the skill must surface that requirement — it cannot pretend to be an authorized agent it isn't.
- **Aggregate data for resale.** Skills don't send user data anywhere except to the necessary regulator/service for the explicit task.

### What skills MUST do

- **Surface human-required steps** via the `requires_human` field
- **Estimate cost and timeline honestly** — based on real-world experience, not optimistic numbers
- **Log every external interaction** to a structured log (without secrets)
- **Validate jurisdictional eligibility** — e.g. a South African company registration skill must reject non-South-African inputs cleanly
- **Respect rate limits** — even when they're not enforced server-side

### Liability

Contributors agree that skills are provided as-is, under Apache 2.0. End users (founders, MIA, integrators) are responsible for verifying outputs before taking irreversible action. Skills are tools, not legal advice. The README of every skill that touches regulated processes must say this explicitly.

---

## Compensation and recognition

Right now, all contributions are free. We will likely introduce a maintainer-compensation model in 2027 for skills that have heavy maintenance burden (e.g. major version updates triggered by regulatory changes). For now, contributing is community service — and excellent visibility for African builders.

Every skill credits its maintainers in `skill.json` and the README. We will also highlight major contributors in the MIA quarterly index publication.

---

## Community

- **GitHub Discussions** — design questions, skill proposals at the brainstorm stage
- **Issues** — concrete proposals, bug reports, feature requests
- **PRs** — actual code
- **Email** — `skills@theaquariusfoundation.org` for anything sensitive or off-public-record

We follow the [Contributor Covenant](https://www.contributor-covenant.org/). Be kind, be specific, be African-context-aware.

---

## Roadmap-level priorities

If you want to contribute and don't have a specific skill in mind, the highest-leverage skills to add right now are:

1. **Company formation across the Big Four** — Nigeria (CAC), Kenya (BRS), Rwanda (RDB) — to pair with the existing SA skill
2. **USD account opening** — Mercury, Wio Bank, Wise Business flows for African founders
3. **Tax filing skills** — VAT (SA, KE, NG), PAYE/UIF (SA), Withholding tax (SA)
4. **DFI grant application skills** — AfDB, IFC, BII, Mastercard Foundation
5. **AfCFTA tariff preference application**
6. **PAPSS settlement integration**
7. **Carbon project registration** — Verra, Gold Standard, Article 6

If you build any of these, you're solving real problems for thousands of founders.

---

*Welcome to the build. Let's make this thing impossible to replicate.*
