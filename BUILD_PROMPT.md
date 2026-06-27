# Claude Code — MIA Skills Kickoff Prompt

Copy everything below this line and paste it as your first message to Claude Code in the `mia-skills` repository.

---

I am Tumelo Ncube, technical founder of MIA (Made in Africa) — an operating system for African entrepreneurship. We are building this together. Before you write any code, read these three files in order:

1. `CLAUDE.md` — orientation and conventions
2. `ARCHITECTURE.md` — the technical architecture
3. `skills/register-company-south-africa/server.py` — the reference implementation

Then summarize back to me, in your own words:
- What this repo is and what it isn't
- What `register-company-south-africa` does today and what's stubbed
- The principles you will follow when writing code here (the ones from CLAUDE.md)

Once I confirm your summary, we will work in this order:

**Phase 1 — Make the scaffold real (Week 1, ~6 focused hours)**

1. Verify the existing skill scaffold runs. Install dependencies, start the server, confirm `get_status` and `estimate_costs` return correct responses. Fix anything broken.
2. Write the `scripts/new-skill.sh` script that generates a new skill directory from a template. It should take a name argument, create the directory layout matching the existing skill, and stub `server.py`, `skill.json`, `README.md`, `pyproject.toml`, and `tests/test_server.py`.
3. Write `scripts/validate_schemas.py` that walks every `skills/*/skill.json` and validates against a JSON schema defined in `scripts/skill.schema.json`. The schema should match what's in CLAUDE.md.
4. Set up GitHub Actions CI — `.github/workflows/ci.yml` exists as a starting point. Verify it runs ruff + pytest on every PR. If anything is missing, fix it.
5. Make a clean first commit with a clear message. We will push to GitHub once Phase 1 is complete.

**Phase 2 — Real implementation of one skill tool (Week 2, ~8 focused hours)**

Pick the highest-leverage real implementation in `register-company-south-africa`: `check_name_availability`. This is the simplest tool that touches real CIPC infrastructure.

1. Research the CIPC e-services name reservation flow. Document what you find in `skills/register-company-south-africa/docs/cipc-research.md`.
2. Decide: is there a usable API, or do we need Playwright? Justify the decision in writing.
3. Implement `check_name_availability` end-to-end against the real CIPC system. Log every interaction. Handle credentials from env. Add tests behind `@pytest.mark.integration` decorator for the live integration; keep unit tests for the parsing/validation logic.
4. Update the skill's status in `skill.json` and `get_status` output to reflect that this one tool is now real.
5. Write a clear PR description for this work.

**Phase 3 — Investor demo prep (Week 3, ~4 focused hours)**

We have an investor meeting where we want to show MIA in action. The demo flow is:
- A founder asks Claude Desktop: "Is 'SunBright Holdings Pty Ltd' available with CIPC?"
- Claude calls our `check_name_availability` tool
- Claude returns the real answer

Help me:
1. Write a `docs/demo.md` that scripts the exact founder-side prompts and expected outputs
2. Generate a clean `claude_desktop_config.json` snippet for connecting to our skill
3. Create a short Loom-style script (text only) I can use to record a 90-second demo video
4. Identify any edge cases that could embarrass us on stage

**Phase 4 — Second skill (Week 4, ~12 focused hours)**

Scaffold and partially implement the second skill. Recommend which one based on:
- Which is most demo-friendly for investors?
- Which has the cleanest integration path (API vs browser automation)?
- Which is the most painful for actual African founders today?

My current shortlist: `claim-section-12j`, `open-usd-account-mercury`, `register-company-kenya`. Make the case for one and start.

---

**Working principles for you (Claude Code):**

- Read CLAUDE.md every session. If anything is unclear, ask before coding.
- Small atomic commits. Clear messages following Conventional Commits.
- No new dependencies without asking. Keep the install surface small.
- Run tests and ruff before suggesting commits.
- When you don't know something specific to South Africa or CIPC, say so and ask me. I'm in Cape Town and have done this in real life.
- If you find yourself writing more than 500 lines of code without a working checkpoint, stop and check in with me.
- We are not racing. We are building a moat. Quality > speed.

**My environment:**

- Windows 10, VSCode, projects on D: drive
- Python 3.12 via official installer
- Git installed and configured
- GitHub account: configured for `aquariusfoundation` org
- Ollama running locally with qwen2.5-coder:7b for quick reference

**My context this week:**

I run multiple ventures (Eduponics, Climate Actions Now, BLASC, BlastBeat, Landmark, others). I am transitioning to focus on MIA as technical founder. My working time on this project is currently 10–15 hours per week, growing over the next 60 days. Plan for that. Don't suggest a sprint that requires 40 hours from me this week.

When ready, start with the summary I asked for at the top. Then we begin Phase 1.
