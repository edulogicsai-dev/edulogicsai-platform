"""
AC8: domains/_contracts/ and nexus/ must contain zero references to specific
agent/domain ids -- only domains/mcat/domain_config.py is allowed to name them.
"""

import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"\b(aria|mira|quinn|mcat)\b", re.IGNORECASE)
DIRS_TO_CHECK = [BACKEND_ROOT / "domains" / "_contracts", BACKEND_ROOT / "nexus"]


def test_no_domain_specific_references_outside_mcat_package() -> None:
    violations = []
    for directory in DIRS_TO_CHECK:
        for path in directory.rglob("*.py"):
            text = path.read_text()
            for lineno, line in enumerate(text.splitlines(), start=1):
                if FORBIDDEN.search(line):
                    violations.append(f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {line.strip()}")

    assert violations == [], "domain-specific references found:\n" + "\n".join(violations)
