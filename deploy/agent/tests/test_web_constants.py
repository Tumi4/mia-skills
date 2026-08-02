"""The landing page's JS constants must equal the Python they were generated from.

This is the guard that makes the page trustworthy. Two copies of a tax threshold
is exactly the failure the whole project argues against, so the JS copy is
generated and this asserts it has not drifted - in CI, on every push.

Kept as a test as well as a CI step so it also fails locally, before a push.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PAGE = REPO_ROOT / "deploy" / "agent" / "static" / "index.html"
GENERATOR = REPO_ROOT / "scripts" / "gen_web_constants.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _js_numbers(source: str, name: str) -> list[float]:
    """Pull every number out of a `const NAME = ...;` line."""
    match = re.search(rf"const {name} = ([^;]+);", source)
    assert match, f"{name} is missing from the generated block"
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]


def test_generator_reports_the_page_is_up_to_date():
    """The generator's own --check, run in-process."""
    generator = _load(GENERATOR, "mia_gen_web_constants")
    current = PAGE.read_text(encoding="utf-8")
    assert generator.splice(current, generator.build_block()) == current, (
        "deploy/agent/static/index.html has drifted from the Python skills. "
        "Run: python scripts/gen_web_constants.py"
    )


def test_turnover_tables_match_the_skill():
    skill = _load(
        REPO_ROOT / "skills" / "calculate-turnover-tax-south-africa" / "server.py",
        "mia_test_turnover",
    )
    page = PAGE.read_text(encoding="utf-8")
    for year, name in ((2027, "T2027"), (2026, "T2026")):
        expected = [value for row in skill.TURNOVER_TAX_TABLES[year] for value in row]
        assert _js_numbers(page, name) == expected


def test_qualifying_limits_match_the_skill():
    skill = _load(
        REPO_ROOT / "skills" / "calculate-turnover-tax-south-africa" / "server.py",
        "mia_test_turnover_limits",
    )
    page = PAGE.read_text(encoding="utf-8")
    assert _js_numbers(page, "LIMIT_NOW") == [
        skill.QUALIFYING_TURNOVER_LIMIT[2027],
        skill.QUALIFYING_TURNOVER_LIMIT[2026],
    ]


def test_vat_thresholds_match_the_skill():
    skill = _load(
        REPO_ROOT / "skills" / "check-vat-registration-south-africa" / "server.py",
        "mia_test_vat",
    )
    page = PAGE.read_text(encoding="utf-8")
    assert _js_numbers(page, "VAT_NOW") == [
        skill.MANDATORY_REGISTRATION_THRESHOLD_ZAR,
        skill.VOLUNTARY_REGISTRATION_MINIMUM_ZAR,
    ]
    assert _js_numbers(page, "VAT_OLD") == [
        skill.PREVIOUS_MANDATORY_THRESHOLD_ZAR,
        skill.PREVIOUS_VOLUNTARY_MINIMUM_ZAR,
    ]
    assert _js_numbers(page, "VAT_DEADLINE_DAYS") == [skill.REGISTRATION_DEADLINE_BUSINESS_DAYS]


def test_the_sentinels_are_intact():
    """Without both fences the generator cannot find its block and CI goes blind."""
    page = PAGE.read_text(encoding="utf-8")
    assert page.count("MIA:GENERATED-CONSTANTS:START") == 1
    assert page.count("MIA:GENERATED-CONSTANTS:END") == 1
    assert page.index("MIA:GENERATED-CONSTANTS:START") < page.index("MIA:GENERATED-CONSTANTS:END")


def test_no_hand_written_thresholds_outside_the_generated_block():
    """A threshold typed into the markup is how the two copies drift apart.

    The page may say "R2.3m" and "R1m" in prose - those are labels, not figures
    the arithmetic depends on. What it must never contain is a second full-precision
    copy of a threshold in the JS outside the fence.
    """
    page = PAGE.read_text(encoding="utf-8")
    script = page[page.index("<script>") :]
    fence_end = script.index("MIA:GENERATED-CONSTANTS:END")
    after_fence = script[fence_end:]
    for literal in ("2300000", "1000000", "120000", "50000", "600000", "950000", "335000"):
        # Digit boundaries, so the slider's MAX = 5000000 does not read as "50000".
        assert not re.search(rf"(?<!\d){literal}(?!\d)", after_fence), (
            f"{literal} is hard-coded in the page's JS outside the generated block - "
            "use the generated constant instead"
        )
