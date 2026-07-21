"""PS303 example mirror stub: ensure examples/04_phone_call_demo.py is syntactically valid."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "04_phone_call_demo.py"


@pytest.fixture
def example_path():
    if not EXAMPLE.exists():
        pytest.skip(f"missing example: {EXAMPLE}")
    return EXAMPLE


def test_04_phone_call_demo_example_compiles(example_path):
    # Arrange
    cmd = [sys.executable, "-m", "py_compile", str(example_path)]

    # Act
    result = subprocess.run(cmd, check=False)

    # Assert
    assert result.returncode == 0
