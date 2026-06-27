# Claude Code — MIA Skills Kickoff Prompt (v2)

Copy everything below the line and paste it as your first message to Claude Code, opened inside the `mia-skills` repository.

This version makes **`calculate-section-12b-solar-deduction`** your first skill — it's live, climate-aligned, pure calculation, and already working with 16 passing tests. (The earlier `register-company-south-africa` skill stays in the repo as skill #2 for later.)

---

I am Tumelo Ncube, technical founder of MIA (Made in Africa) — an operating system for African entrepreneurship. We're building this together. Before writing any code, read these files in order:

1. `CLAUDE.md` — orientation and conventions
2. `ARCHITECTURE.md` — the technical architecture
3. `skills/calculate-section-12b-solar-deduction/server.py` — the working reference skill
4. `skills/calculate-section-12b-solar-deduction/tests/test_server.py` — how we test

Then summarize back to me, in your own words:
- What this repo is and isn't
- What the Section 12B skill calculates, and why it returns `requires_human: true`
- The principles you'll follow when writing code here

Once I confirm your summary, we work in this order:

**Phase 1 — Verify and harden the 12B skill (Week 1, ~4 hours)**

1. Install and run it. `pip install -e ".[dev]"`, then `pytest`. Confirm all 16 tests pass on my machine.
2. Run the server (`python server.py`) and confirm it starts as an MCP server.
3. Review my tax constants against current SARS rules. Flag anything that looks stale. (Personal brackets are 2026 year-of-assessment; corporate rate 27%; 12BA expired 28 Feb 2025.) Do NOT change numbers without showing me the source.
4. Add 3–5 more edge-case tests you think are missing (e.g. zero taxable income, trust taxpayer, very large grant portion).
5. Add a `ruff` pass and fix any lint. Clean commit.

**Phase 2 — Make it demo-perfect (Week 1–2, ~3 hours)**

1. Write `skills/calculate-section-12b-solar-deduction/docs/demo.md` scripting the exact founder prompts and expected Claude responses for an investor demo.
2. Generate the `claude_desktop_config.json` snippet to connect this skill.
3. Test the full flow through Claude Desktop on my machine and fix anything awkward.
4. Write a 60-second demo script (text) I can use to record a video.

**Phase 3 — Repo foundation (Week 2, ~4 hours)**

1. Verify `CLAUDE.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `README.md` are all coherent and current.
2. Write `scripts/new-skill.sh` that scaffolds a new skill directory from a template matching the 12B skill's layout.
3. Write `scripts/validate_schemas.py` + `scripts/skill.schema.json` to validate every `skill.json`.
4. Confirm `.github/workflows/ci.yml` runs ruff + pytest across all skills. Fix if needed.
5. First clean push to GitHub.

**Phase 4 — Second skill (Week 3–4, ~10 hours)**

The repo already contains a scaffolded `register-company-south-africa` skill (CIPC company registration) with stubbed tools. Pick up that skill and implement its first real tool, `check_name_availability`, against the CIPC system. Research first, document the approach, decide API-vs-Playwright, then build. Tests required.

---

**Working principles for you (Claude Code):**

- Read `CLAUDE.md` every session. Ask before coding if anything is unclear.
- Small atomic commits, Conventional Commits format.
- No new dependencies without asking.
- Run `pytest` and `ruff` before suggesting any commit.
- For anything tax/regulatory, never invent a number — cite the SARS source or ask me.
- If you're writing >500 lines without a working checkpoint, stop and check in.
- Quality over speed. We're building a moat, not racing.

**My environment (new PC):**

- Windows 11, VSCode
- Python 3.12 (official installer)
- Git for Windows installed
- GitHub: `aquariusfoundation` org
- Working ~10–15 hours/week on this during my venture transition — don't plan 40-hour sprints.

When ready, start with the summary I asked for. Then we begin Phase 1.
