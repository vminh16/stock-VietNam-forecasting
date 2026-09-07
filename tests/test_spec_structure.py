"""Guard the split of SPEC.md into a contract, its registrations and its evidence.

Section numbers are cited from code, from configs, from tests, and from report
files that are frozen artifacts and must never be rewritten. So the split moved
content without renumbering anything, and these tests keep it that way.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC = ROOT / "SPEC.md"
REGISTRATIONS = ROOT / "docs" / "registrations"
EVIDENCE = ROOT / "docs" / "evidence"

HEADING = re.compile(r"^### (\d+\.\d+) ", re.MULTILINE)
CITATION = re.compile(r"(?:SPEC|[Ss]ection)\s+(\d+\.\d+)")
SEARCHED = ("*.py", "*.yaml", "*.yml")
SEARCHED_DIRS = ("evaluation", "tests", "data_pipeline")


def numbered_sections():
    """Every `### N.M` heading, wherever the split put it."""
    found = {}
    for path in [SPEC, *sorted(REGISTRATIONS.glob("*.md")), *sorted(EVIDENCE.glob("*.md"))]:
        if path.name == "README.md":
            continue
        for number in HEADING.findall(path.read_text(encoding="utf-8")):
            found.setdefault(number, []).append(path.relative_to(ROOT).as_posix())
    return found


def test_no_section_number_is_defined_twice():
    duplicates = {n: where for n, where in numbered_sections().items() if len(where) > 1}
    assert duplicates == {}


def test_the_moved_sections_left_the_spec_and_landed_in_their_directory():
    sections = numbered_sections()
    for number in ("3.1", "3.5", "3.9", "3.10"):
        assert sections[number] == [
            f"docs/evidence/{Path(sections[number][0]).name}"
        ], number
    for number in ("8.6", "8.9", "8.12", "8.13"):
        assert sections[number] == [
            f"docs/registrations/{Path(sections[number][0]).name}"
        ], number
    # The contract stayed put.
    for number in ("8.1", "8.2", "8.5"):
        assert sections[number] == ["SPEC.md"], number


def test_the_spec_indexes_every_moved_section():
    """A citation of a moved section must be resolvable from SPEC.md alone."""
    spec = SPEC.read_text(encoding="utf-8")
    for path in sorted(REGISTRATIONS.glob("*.md")) + sorted(EVIDENCE.glob("*.md")):
        if path.name == "README.md":
            continue
        link = path.relative_to(ROOT).as_posix()
        assert link in spec, f"SPEC.md does not link {link}"


def test_every_cited_section_still_exists():
    """Nothing in code, configs or tests may cite a number the split lost."""
    known = set(numbered_sections())
    missing = {}
    for directory in SEARCHED_DIRS:
        for pattern in SEARCHED:
            for path in (ROOT / directory).rglob(pattern):
                if "__pycache__" in path.parts:
                    continue
                for number in CITATION.findall(path.read_text(encoding="utf-8")):
                    if number not in known:
                        missing.setdefault(number, set()).add(
                            path.relative_to(ROOT).as_posix()
                        )
    assert missing == {}


def test_each_directory_carries_an_index():
    for directory in (REGISTRATIONS, EVIDENCE):
        readme = directory / "README.md"
        assert readme.exists()
        text = readme.read_text(encoding="utf-8")
        for path in sorted(directory.glob("*.md")):
            if path.name == "README.md":
                continue
            assert path.name in text, f"{readme} does not index {path.name}"


@pytest.mark.parametrize("directory", ["registrations", "evidence"])
def test_a_moved_file_holds_exactly_one_section(directory):
    for path in sorted((ROOT / "docs" / directory).glob("*.md")):
        if path.name == "README.md":
            continue
        numbers = HEADING.findall(path.read_text(encoding="utf-8"))
        assert len(numbers) == 1, path
        assert path.name.startswith(numbers[0] + "-"), path
