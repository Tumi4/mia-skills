# 30-Day Build Plan — mia-skills

A realistic plan for the first month, calibrated for ~10–15 hours/week of focused founder time. Designed to ship one working demo skill in time for the next investor meeting, build foundational tooling, and establish the open-source rhythm.

---

## Week 1 — Foundation (6 focused hours)

**Goal:** The repo lives, the scaffold runs, the developer experience is right.

### Day 1 — Setup (1.5 hours)

- [ ] Create the GitHub repo: `aquariusfoundation/mia-skills` (public, Apache 2.0 license)
- [ ] Push the starter scaffold (the files in `/home/claude/mia-skills/` from Claude)
- [ ] Verify `pip install -e ".[dev]"` works in `skills/register-company-south-africa/`
- [ ] Run `pytest` — confirm tests pass
- [ ] Run `python server.py` — confirm MCP server starts

### Day 2 — Developer tooling (2 hours)

- [ ] Pair with Claude Code on `scripts/new-skill.sh` (skill scaffolding generator)
- [ ] Pair with Claude Code on `scripts/validate_schemas.py` (schema validator)
- [ ] Define `scripts/skill.schema.json` (formal JSON schema for skill.json)
- [ ] Test: generate a dummy skill via the script, verify it validates

### Day 3 — CI and polish (1.5 hours)

- [ ] Push `.github/workflows/ci.yml`
- [ ] Verify CI runs green on `main`
- [ ] Add branch protection: PRs require CI pass + 1 review
- [ ] Set up GitHub Discussions for skill proposals
- [ ] Add CODEOWNERS file

### Day 4 — Public launch readiness (1 hour)

- [ ] Final review of README, CLAUDE.md, ARCHITECTURE.md, CONTRIBUTING.md
- [ ] Add issue templates: bug, skill proposal, question
- [ ] Add PR template
- [ ] Create a `v0.1.0-scaffold` git tag

**Milestone:** Repo is live, public, CI green, ready for outside contributors to look at.

**Don't do this week:** Don't try to implement real CIPC integration. The scaffold quality matters more than the first feature.

---

## Week 2 — First real implementation (8 focused hours)

**Goal:** `check_name_availability` works end-to-end against real CIPC.

### Day 1 — Research (2 hours)

- [ ] Pair with Claude Code on CIPC research
- [ ] Document findings in `skills/register-company-south-africa/docs/cipc-research.md`
- [ ] Decide: Playwright vs API. Document the decision.
- [ ] Set up `.env.local` with real CIPC credentials (add `.env.local` to `.gitignore` if not already)

### Day 2 — Implementation, part 1 (2.5 hours)

- [ ] Build the CIPC login flow as a reusable `CIPCSession` class in `src/register_company_south_africa/client.py`
- [ ] Add session reuse / cookie persistence (within a single skill invocation)
- [ ] Unit tests for parsing logic
- [ ] Commit: `feat(register-company-sa): implement CIPC session client`

### Day 3 — Implementation, part 2 (2 hours)

- [ ] Wire `check_name_availability` to actually use `CIPCSession`
- [ ] Add structured logging
- [ ] Handle: name available, name taken, name flagged as misleading, similar-name conflicts
- [ ] Integration test behind `@pytest.mark.integration`
- [ ] Commit: `feat(register-company-sa): real CIPC name availability check`

### Day 4 — Polish and PR (1.5 hours)

- [ ] Update `skill.json` to reflect new status (one tool live)
- [ ] Update `get_status` output
- [ ] Update README with working example
- [ ] Self-review the diff
- [ ] Push PR, watch CI go green, merge

**Milestone:** One real tool, end-to-end, against production CIPC, with tests. The skill moves from "scaffold" to "alpha" in `skill.json`.

**Don't do this week:** Don't expand scope to more tools yet. One real working tool teaches you 10x what three half-built ones do.

---

## Week 3 — Investor demo prep (4 focused hours)

**Goal:** A clean 90-second demo for the next investor meeting.

### Day 1 — Demo script (1.5 hours)

- [ ] Write `docs/demo.md` with the exact founder prompts and Claude responses
- [ ] Test with real names you'll demo (have 3 prepped: one available, one taken, one borderline)
- [ ] Generate the `claude_desktop_config.json` snippet for the demo machine

### Day 2 — Record (1 hour)

- [ ] Set up Loom or OBS
- [ ] Do 3 takes. Pick the cleanest.
- [ ] Trim to <90 seconds
- [ ] Upload, get share link

### Day 3 — Talking points (1 hour)

- [ ] Write the verbal explanation that goes with the demo:
  - "This is the open-source moat — anyone can contribute"
  - "This skill doesn't exist anywhere else — not in OpenAI's store, not in any startup's product"
  - "Multiply this by 200 skills across 54 jurisdictions and you have the African operational stack"
  - "MIA's hosted product (the portal Michael built) composes these into agentic workflows"

### Day 4 — Rehearsal (30 min)

- [ ] Run the demo cold for someone (Mikhail, Robert, anyone) and time it
- [ ] Adjust based on feedback

**Milestone:** Demo ready. Embed in next pitch deck. Send video to next 3 investor conversations.

---

## Week 4 — Second skill scaffold + community (12 focused hours)

**Goal:** Prove the pattern is repeatable. Plant the community seed.

### Days 1–2 — Pick and scaffold second skill (4 hours)

Decision criteria:
- **Demo value:** Will an investor's eyes light up?
- **Implementation tractability:** API > browser automation
- **Founder pain:** How much does this hurt today?

Recommended pick: **`claim-section-12j`** (SA tax incentive calculator)
- Demo value: HIGH — "calculate my Section 12J tax saving for this investment" is concrete and beloved
- Tractability: HIGH — it's a calculator over SARS-published rules, no browser automation needed
- Pain: HIGH — most founders don't know they qualify

Alternative pick: **`register-company-kenya`** (CAC equivalent)
- Demo value: HIGH — extends the pattern across jurisdictions visually
- Tractability: MEDIUM — Kenya's BRS has more API surface than CIPC
- Pain: HIGH

### Days 3–4 — Initial implementation (4 hours)

- [ ] Use `scripts/new-skill.sh` to scaffold
- [ ] Implement the 2–3 most valuable tools end-to-end
- [ ] Tests, docs, PR
- [ ] Tag as `alpha`

### Day 5 — Community launch (2 hours)

- [ ] Write a launch blog post: "Introducing mia-skills"
- [ ] Post on:
  - Hacker News (timing matters; aim for Tue/Wed 8am PST)
  - LinkedIn (Tumelo + Michael + Aquarius)
  - Twitter/X
  - Africa Tech Slack/Discord communities (Future Africa, Open Africa, Africa Builders)
  - r/Africa, r/python on Reddit
- [ ] Soft launch to Endeavor, Norrsken, MEST, Antler Africa networks

### Day 6 — Respond and shape (2 hours)

- [ ] Respond to GitHub issues, PRs, discussion threads
- [ ] Triage skill proposals — Approve, Refine, or Park
- [ ] Update the "Available skills" table in README weekly

**Milestone:** Two working skills. Public community. First outside skill proposal landed.

---

## Month 2 onwards — Cadence to maintain

Weekly:
- 1 hour: triage issues, review PRs
- 4 hours: extend or add skills (target: 2 new skills per month)
- 1 hour: write a "skill of the month" highlight for the MIA newsletter

Monthly:
- Refresh the README's "Available skills" table
- Publish a community update (what landed, what's next, who contributed)
- Review CLAUDE.md and ARCHITECTURE.md — update if patterns have evolved

Quarterly:
- Tag a release (v0.2, v0.3...)
- Publish the African Climate Capital Index (using outcome data from skills usage, anonymized)
- Review acquisition targets (VC4Africa, Briter Bridges) — is consolidation conversation worth opening yet?

---

## Time budget sanity check

| Phase | Your hours | Calendar |
|---|---|---|
| Week 1 (foundation) | 6 | 4 days × 1.5 hrs |
| Week 2 (first impl) | 8 | 4 days × 2 hrs |
| Week 3 (demo prep) | 4 | 3 days × 1.3 hrs |
| Week 4 (second skill + launch) | 12 | 6 days × 2 hrs |
| **Month 1 total** | **30 hours** | |
| Month 2+ ongoing | ~6 hrs/week | |

This is genuinely doable alongside your other ventures during the transition. The Eduponics handover to Mikhail and the BlastBeat / Climate Actions Now operational rhythms continue uninterrupted. MIA work is bounded.

---

## What success looks like at Day 30

- Repo: public, 2 working skills, CI green, clean history
- Community: 3+ skill proposals open, 1+ external contributor interested
- Investor: demo recorded, in next pitch
- Personal: rhythm established, you know your weekly hour budget, momentum without burnout
- Michael: confidence that his technical founder is real

---

*"The matching platform is the wedge. The skills library is the moat. Two weekends of focused build proves the vision is real."*
