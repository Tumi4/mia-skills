# MIA Build — New PC Setup (Windows 11)

Your exact path from a fresh Windows 11 machine to Claude Code building MIA. Do these in order. Don't move on until each step works.

Total setup time: ~25 minutes, then you're building.

---

## Step 1 — Install Git for Windows (5 min)

Claude Code needs Git.

1. Go to **git-scm.com** → Download for Windows
2. Run the installer with **default settings** — just keep clicking Next
3. Make sure **"Add Git to PATH"** stays checked (it's the default)
4. Verify: open **PowerShell** and run:
   ```powershell
   git --version
   ```
   You should see a version number.

---

## Step 2 — Install Claude Code (5 min)

1. Open **Windows PowerShell** — the 64-bit one. NOT the x86 version, NOT Git Bash, NOT Command Prompt.
2. Run:
   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```
3. **Close PowerShell completely. Open a brand-new PowerShell window.** (The PATH doesn't update until you do this — this is the #1 cause of "claude not recognized" errors.)
4. Verify:
   ```powershell
   claude --version
   claude doctor
   ```
   `claude doctor` checks your install, auth, and config.

If `claude` is not recognized: confirm `%USERPROFILE%\.local\bin` is in your PATH, then reopen PowerShell.

**Note on subscription:** Claude Code needs an active plan. Your Pro plan works, but for a multi-week build, the quota on Pro will interrupt you often. If cash flow allows, **Max 5x ($100/mo)** gives you the headroom to actually build without constant stops. Your call.

---

## Step 3 — Install Python 3.12 (5 min)

1. Go to **python.org/downloads** → Download Python 3.12.x
2. Run the installer. **CRITICAL: check "Add python.exe to PATH"** at the bottom of the first screen before clicking Install.
3. Verify in a new PowerShell window:
   ```powershell
   python --version
   pip --version
   ```

---

## Step 4 — Get the repo onto your machine (5 min)

1. Download the **mia-skills-starter-v2.zip** I gave you.
2. Unzip it to a clean projects folder. I suggest:
   ```
   C:\Users\<you>\projects\mia-skills
   ```
   (On your old machine you used D:. On this new one, pick whatever drive you want — just remember the path.)
3. In PowerShell:
   ```powershell
   cd C:\Users\<you>\projects\mia-skills
   git init
   git add .
   git commit -m "chore: initial scaffold from starter kit"
   ```

---

## Step 5 — Confirm the 12B skill works BEFORE Claude Code touches it (3 min)

This proves your environment is good and the skill is real.

```powershell
cd C:\Users\<you>\projects\mia-skills\skills\calculate-section-12b-solar-deduction
pip install -e ".[dev]"
pytest
```

You should see **16 tests pass**. If they do, your Python environment is correct and the skill works on your machine. (I already verified these pass — you're just confirming on your hardware.)

Quick live check of the actual calculation:

```powershell
python -c "import asyncio, sys; sys.path.insert(0,'.'); from server import calculate_deduction, DeductionInput, TaxpayerType; out=asyncio.run(calculate_deduction(DeductionInput(equipment_cost_zar=500000, taxpayer_type=TaxpayerType.company, taxable_income_zar=2000000))); print('Deduction:', out.deduction_zar, '| Saving:', out.cash_tax_saving_zar)"
```

Expected: `Deduction: 500000.0 | Saving: 135000.0`

---

## Step 6 — Launch Claude Code and start building (2 min)

```powershell
cd C:\Users\<you>\projects\mia-skills
claude
```

First launch opens your browser to sign in with your Anthropic account.

Once you're at the Claude Code prompt:
1. Open **MIA_Claude_Code_Kickoff_Prompt_v2.md**
2. Copy everything below the `---` line
3. Paste it as your first message

Claude Code reads the orientation files, summarizes back to you, you confirm — and you're in Phase 1.

---

## (Optional, later) Create the GitHub repo

When you're ready to push public:

If you have GitHub CLI (`gh`):
```powershell
gh repo create aquariusfoundation/mia-skills --public --source=. --push
```

If not, create the repo manually on github.com under the `aquariusfoundation` org, then:
```powershell
git remote add origin https://github.com/aquariusfoundation/mia-skills.git
git branch -M main
git push -u origin main
```

Don't rush this. Get the skill solid locally first. Push when Phase 1 is done.

---

## If something breaks

- **"claude not recognized"** → close and reopen PowerShell; check `%USERPROFILE%\.local\bin` in PATH
- **"python not recognized"** → you missed "Add to PATH" in the installer; reinstall and check the box
- **pip install fails on a package** → run `pip install --upgrade pip` first, then retry
- **tests fail** → paste the error to Claude Code; it'll diagnose. Don't push past a red test.
- **Raw mode is not supported** → you're in Git Bash; switch to PowerShell

---

## What you have when this is done

- A working Section 12B solar tax calculator skill — your first MIA skill, live and demoable
- Claude Code wired into the repo, ready to build skill #2
- A clean local git history
- The exact rhythm you'll use for every future skill

That's the foundation. The moat starts here.
