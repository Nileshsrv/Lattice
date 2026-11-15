"""A-14 (lite): physics/tool modules may not hand-type physical constants (I-12).

Heuristic: a float literal with >= 6 significant digits in a scanned module is
treated as a hand-typed constant. constants.py is the single allowed source.
"""

import ast
import re
from pathlib import Path

LATTICE = Path(__file__).resolve().parents[1] / "lattice"
SCANNED = [LATTICE / "physics", LATTICE / "tools"]
ALLOWED_FILES = {LATTICE / "physics" / "constants.py"}


def _significant_digits(value: float) -> int:
    mantissa = re.sub(r"[eE][+-]?\d+$", "", repr(value))
    digits = re.sub(r"[^0-9]", "", mantissa).lstrip("0").rstrip("0")
    return len(digits)


def test_no_hand_typed_constants():
    offenders: list[str] = []
    for root in SCANNED:
        for path in root.rglob("*.py"):
            if path in ALLOWED_FILES:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    if _significant_digits(node.value) >= 6:
                        offenders.append(f"{path.name}:{node.lineno} -> {node.value!r}")
    assert not offenders, (
        "hand-typed high-precision float literals found (import from "
        f"lattice.physics.constants instead): {offenders}"
    )


def test_constants_come_from_scipy():
    import scipy.constants as sc

    from lattice.physics import constants

    assert constants.h == sc.h
    assert constants.c == sc.c
    assert constants.k_B == sc.k
    assert constants.sigma_sb == sc.sigma
    assert constants.b_wien == sc.Wien
    assert constants.m_e == sc.m_e
    assert "CODATA" in constants.CODATA_SOURCE
