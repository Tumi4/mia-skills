# Section 12B skill — investor demo script

A tight, repeatable demo of the `calculate-section-12b-solar-deduction` skill running
live inside **Claude Desktop**. Every number below is the **real output** of the skill
(captured from the MCP server, not illustrative). If the skill's output ever stops
matching this script, that's a regression — fix the skill, not the script.

> One-line pitch for the room: *"Watch an AI agent do South African tax engineering
> that today requires a consultant — instantly, with the regulatory nuance built in."*

---

## 0. Before the room (one-time setup)

1. Confirm the skill is installed and green:
   ```powershell
   cd C:\Users\tumel\projects\mia-skills\skills\calculate-section-12b-solar-deduction
   python -m pytest -q
   ```
   Expect `21 passed`.

2. Connect the skill to Claude Desktop. Open
   `%APPDATA%\Claude\claude_desktop_config.json` and merge in the `section-12b` block
   from [`claude_desktop_config.example.json`](./claude_desktop_config.example.json)
   (paths are machine-specific — adjust if your layout differs).

3. **Fully quit and reopen Claude Desktop** (config is only read on launch).

4. Verify the connection: in a new chat, click the tools/plug icon — you should see
   **section-12b** with four tools: `calculate_deduction`, `compare_12b_vs_12ba`,
   `check_eligibility`, `get_status`. Or just type *"What section-12b tools do you have?"*

5. Have this scenario memorised: **R650,000 solar system, R100,000 install labour,
   a company, R3,000,000 taxable income.**

---

## 1. The demo flow (≈3 minutes)

Four beats: **eligibility → headline number → the nuance → the regulatory depth.**
Read the founder prompt verbatim; let Claude call the tool live.

### Beat 1 — "Do I even qualify?"

**You type:**
> A client runs a profitable manufacturing company and wants to install commercial
> rooftop solar. They'll own the system, it's brand new, and they'll get a Certificate
> of Compliance. Do they qualify for the Section 12B deduction?

**Claude calls** `check_eligibility` and answers:
> ✅ **Eligible.** All core SARS conditions are met (business use, ownership, new &
> unused, Certificate of Compliance). Next step: calculate the benefit.

**Talking point:** *"The skill encodes the actual SARS eligibility gates — business
use, ownership, CoC, new-and-unused. It won't hand you a number you can't defend."*

### Beat 2 — "What's it actually worth?" (the headline)

**You type:**
> Great. The system is R650,000 of equipment plus R100,000 installation labour. The
> company has R3,000,000 taxable income this year. Calculate the Section 12B benefit.

**Claude calls** `calculate_deduction` and answers with:

| Figure | Value |
|---|---|
| Section applied | Section 12B (100%) |
| Qualifying cost | **R650,000** |
| Deduction | **R650,000** |
| Cash tax saving | **R175,500** |
| Total project cost | R750,000 |
| Effective net cost | **R574,500** |

> ⚠️ Plus a `requires_human` block: get a valid CoC, itemise equipment vs labour on
> the invoice, confirm the commissioning date falls in the tax year, and have a
> registered tax practitioner confirm the claim before filing.

**Talking point:** *"R175,500 of real cash back, at the 27% company rate. Notice two
things it got right without being told: it **excluded the R100,000 labour** — SARS
doesn't allow 12B on labour — and it's **honest about the human steps**. It's not
pretending to be your tax practitioner."*

### Beat 3 — "Does it understand who's claiming?" (the nuance)

**You type:**
> What if instead it's a sole proprietor — an individual — with R900,000 taxable
> income buying a smaller R120,000 system?

**Claude calls** `calculate_deduction` with `taxpayer_type: sole_proprietor` and answers:

| Figure | Value |
|---|---|
| Marginal rate used | **41%** |
| Deduction | R120,000 |
| Cash tax saving | **R47,060** |
| Effective net cost | **R72,940** |

**Talking point:** *"Same skill, completely different tax logic. For an individual it
runs the **2027 SARS progressive brackets** and gives relief at the **marginal rate** —
here 41%. A company gets a flat 27%; an ordinary trust gets a flat 45%; a special trust
goes back on the individual table. That distinction is the kind of thing founders get
wrong and consultants charge for. It's baked in."*

### Beat 4 — "Is this number current?" (the regulatory depth)

**You type:**
> I heard there was a 125% solar allowance. Are we leaving money on the table?

**Claude calls** `compare_12b_vs_12ba` and answers:

| | Section 12B (live) | Section 12BA (expired) |
|---|---|---|
| Rate | 100% | 125% |
| Deduction | R650,000 | R812,500 |
| Cash saving | **R175,500** | R219,375 |
| Status | Active, permanent | **Expired 28 Feb 2025** |

> Benefit lost to the 12BA expiry: **R43,875**. Takeaway: 12B alone is still a 100%
> year-one deduction and remains compelling for commercial solar.

**Talking point:** *"This is the moat. The enhanced 125% allowance **expired on
28 February 2025**. A model trained on older data — or a founder Googling — would
happily quote 125% and overstate the claim. The skill knows the rule lapsed, quotes
the **live** number, and shows exactly what the expiry cost. Current, jurisdiction-
specific, regulator-accurate."*

---

## 2. The close (15 seconds)

> *"That's one skill, in one jurisdiction. The thesis is hundreds of these — company
> registration, banking, grants, filings — across 54 countries, all open-source and
> callable by any AI. The African founder's operating system, as composable
> infrastructure. This is layer two."*

---

## 3. 60-second video script (for recording)

Tight cut for a screen-recording. `[SCREEN]` = what's on screen, `[VO]` = voiceover.

```
0:00–0:06   [SCREEN] Claude Desktop, section-12b tools visible in the tool menu.
            [VO] "This is Claude, with a Made-in-Africa tax skill plugged in."

0:06–0:20   [SCREEN] Type Beat 2 prompt (R650k system, company, R3m income). Send.
            [VO] "I ask it what a R650,000 commercial solar system is worth under
                  South Africa's Section 12B."

0:20–0:32   [SCREEN] Result table appears: R650k deduction, R175,500 saving,
                     R574,500 net cost.
            [VO] "R175,500 back in cash. It excluded the install labour automatically —
                  because SARS doesn't allow it — and flagged the human steps."

0:32–0:46   [SCREEN] Type Beat 4 prompt ("isn't there a 125% allowance?"). Send.
            [VO] "Most tools would quote the old 125% rate."

0:46–0:56   [SCREEN] Comparison table: 12BA EXPIRED 28 Feb 2025, R43,875 lost.
            [VO] "This one knows that allowance expired in February 2025. It quotes the
                  live number — and shows what the expiry cost."

0:56–1:00   [SCREEN] Cut to repo / MIA logo.
            [VO] "Open-source. Africa-first. This is MIA."
```

**Recording tips:** pre-load the prompts in a text file to paste cleanly; do one dry
run so the tool-permission dialog is already approved; keep the cursor still while
results render.

---

## 4. If something goes wrong (live recovery)

- **Tool doesn't appear:** you didn't fully restart Claude Desktop, or a JSON syntax
  error in the config. Validate the config, quit Claude *completely* (check the tray),
  relaunch.
- **"Module not found" / server won't start:** the `command` path points at a Python
  without the deps. Use the interpreter where you ran `pip install -e ".[dev]"` (see
  the example config), or re-run that install.
- **Numbers differ from this script:** a SARS constant or the logic changed. Run
  `python -m pytest -q`; the tests pin the reference figures and will localise the drift.
- **A number looks wrong on stage:** fall back to the honesty line — *"it's a
  calculation tool, not tax advice; a practitioner signs off"* — and move on. The
  `requires_human` framing makes that a feature, not an excuse.

> Note on input shape: `calculate_deduction` takes its arguments under an `input`
> object (house style — see `CLAUDE.md`); the other three tools take flat arguments.
> Claude handles both transparently, so it never surfaces in the demo.
