#!/usr/bin/env python3
# File: /home/ywatanabe/proj/scitex-notification/tests/test_env_loader.py
"""Tests for the environment variable loader.

Covers:
- parse_src_file() with a temp file
- _parse_value() quote handling
- load_env_from_path() with nonexistent path
- load_scitex_notification_env() when env var is set / not set
"""

from __future__ import annotations

import os
import textwrap
from contextlib import contextmanager


@contextmanager
def _scoped_env(overrides: dict[str, str | None]):
    """Set/remove env vars and restore originals on exit.

    A value of None removes the variable for the duration of the context.
    Real os.environ mutation — no mock library involved.
    """
    saved: dict[str, str | None] = {}
    try:
        for key, value in overrides.items():
            saved[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, prior in saved.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


# ---------------------------------------------------------------------------
# test_parse_src_file_basic
# ---------------------------------------------------------------------------
def test_parse_src_file_extracts_plain_key_value_pairs(tmp_path):
    """parse_src_file() extracts plain KEY=VALUE pairs."""
    # Arrange
    from scitex_notification._env_loader import parse_src_file

    src = tmp_path / "test.src"
    src.write_text(
        textwrap.dedent("""\
            FOO=bar
            BAZ=qux
        """)
    )

    # Act
    result = parse_src_file(src)

    # Assert
    assert result == {"FOO": "bar", "BAZ": "qux"}


# ---------------------------------------------------------------------------
# test_parse_src_file_export_prefix
# ---------------------------------------------------------------------------
def test_parse_src_file_strips_export_prefix(tmp_path):
    """parse_src_file() strips 'export ' prefix."""
    # Arrange
    from scitex_notification._env_loader import parse_src_file

    src = tmp_path / "test.src"
    src.write_text("export MY_VAR=hello\n")

    # Act
    result = parse_src_file(src)

    # Assert
    assert result["MY_VAR"] == "hello"


# ---------------------------------------------------------------------------
# test_parse_src_file_comments_and_blank_lines
# ---------------------------------------------------------------------------
def test_parse_src_file_ignores_comments_and_blanks(tmp_path):
    """parse_src_file() ignores comment lines and blank lines."""
    # Arrange
    from scitex_notification._env_loader import parse_src_file

    src = tmp_path / "test.src"
    src.write_text(
        textwrap.dedent("""\
            # This is a comment

            KEY=value
            # Another comment
        """)
    )

    # Act
    result = parse_src_file(src)

    # Assert
    assert result == {"KEY": "value"}


# ---------------------------------------------------------------------------
# test_parse_value_double_quotes
# ---------------------------------------------------------------------------
def test_parse_value_strips_surrounding_double_quotes():
    """_parse_value() removes surrounding double quotes."""
    # Arrange
    from scitex_notification._env_loader import _parse_value

    # Act
    result = _parse_value('"hello world"')

    # Assert
    assert result == "hello world"


def test_parse_value_strips_surrounding_single_quotes():
    """_parse_value() removes surrounding single quotes."""
    # Arrange
    from scitex_notification._env_loader import _parse_value

    # Act
    result = _parse_value("'hello world'")

    # Assert
    assert result == "hello world"


def test_parse_value_leaves_plain_value_unchanged():
    """_parse_value() leaves plain values unchanged."""
    # Arrange
    from scitex_notification._env_loader import _parse_value

    # Act
    result = _parse_value("plain_value")

    # Assert
    assert result == "plain_value"


def test_parse_value_handles_empty_string_input():
    """_parse_value() handles empty string."""
    # Arrange
    from scitex_notification._env_loader import _parse_value

    # Act
    result = _parse_value("")

    # Assert
    assert result == ""


def test_parse_value_expands_dollar_var_reference():
    """_parse_value() expands $VAR references from os.environ."""
    # Arrange
    from scitex_notification._env_loader import _parse_value

    # Act
    with _scoped_env({"_TEST_EXPAND": "world"}):
        result = _parse_value("hello_$_TEST_EXPAND")
    # The variable name _TEST_EXPAND should be expanded
    expanded = "world" in result or result == "hello_world"

    # Assert
    assert expanded


# ---------------------------------------------------------------------------
# test_load_env_from_nonexistent_path
# ---------------------------------------------------------------------------
def test_load_env_from_path_returns_empty_for_missing_path():
    """load_env_from_path() returns empty dict for a nonexistent path."""
    # Arrange
    from scitex_notification._env_loader import load_env_from_path

    # Act
    result = load_env_from_path("/nonexistent/path/that/does/not/exist.src")

    # Assert
    assert result == {}


# ---------------------------------------------------------------------------
# test_load_env_from_file_path
# ---------------------------------------------------------------------------
def test_load_env_from_path_loads_single_src_file(tmp_path):
    """load_env_from_path() loads variables from a single .src file."""
    # Arrange
    from scitex_notification._env_loader import load_env_from_path

    src = tmp_path / "config.src"
    src.write_text("LOADED_KEY=loaded_value\n")

    # Act
    result = load_env_from_path(str(src))

    # Assert
    assert result["LOADED_KEY"] == "loaded_value"


# ---------------------------------------------------------------------------
# test_load_env_from_directory
# ---------------------------------------------------------------------------
def test_load_env_from_directory_loads_src_files_only(tmp_path):
    """load_env_from_path() loads *.src files from a directory."""
    # Arrange
    from scitex_notification._env_loader import load_env_from_path

    (tmp_path / "a.src").write_text("VAR_A=alpha\n")
    (tmp_path / "b.src").write_text("VAR_B=beta\n")
    (tmp_path / "notasrc.txt").write_text("IGNORED=yes\n")

    # Act
    result = load_env_from_path(str(tmp_path))

    # Assert
    assert result == {"VAR_A": "alpha", "VAR_B": "beta"}


# ---------------------------------------------------------------------------
# test_load_scitex_notification_env_no_var_set
# ---------------------------------------------------------------------------
def test_load_scitex_notification_env_returns_zero_when_var_unset():
    """load_scitex_notification_env() returns 0 when env var is not set."""
    # Arrange
    from scitex_notification._env_loader import load_scitex_notification_env

    # Act
    with _scoped_env({"SCITEX_NOTIFICATION_ENV_SRC": None}):
        count = load_scitex_notification_env()

    # Assert
    assert count == 0


# ---------------------------------------------------------------------------
# test_load_scitex_notification_env_with_file
# ---------------------------------------------------------------------------
def test_load_scitex_notification_env_reports_loaded_count(tmp_path):
    """load_scitex_notification_env() returns count of variables loaded."""
    # Arrange
    from scitex_notification._env_loader import load_scitex_notification_env

    src = tmp_path / "notify.src"
    src.write_text(
        textwrap.dedent("""\
            SCITEX_TEST_LOADED_A=value_a
            SCITEX_TEST_LOADED_B=value_b
        """)
    )

    # Act
    with _scoped_env(
        {
            "SCITEX_NOTIFICATION_ENV_SRC": str(src),
            "SCITEX_TEST_LOADED_A": None,
            "SCITEX_TEST_LOADED_B": None,
        }
    ):
        count = load_scitex_notification_env()
        # Clean up env vars set by loader
        os.environ.pop("SCITEX_TEST_LOADED_A", None)
        os.environ.pop("SCITEX_TEST_LOADED_B", None)

    # Assert
    assert count == 2


def test_load_scitex_notification_env_writes_value_a_to_environ(tmp_path):
    """load_scitex_notification_env() injects loaded variables into os.environ."""
    # Arrange
    from scitex_notification._env_loader import load_scitex_notification_env

    src = tmp_path / "notify.src"
    src.write_text(
        textwrap.dedent("""\
            SCITEX_TEST_LOADED_A=value_a
            SCITEX_TEST_LOADED_B=value_b
        """)
    )

    # Act
    with _scoped_env(
        {
            "SCITEX_NOTIFICATION_ENV_SRC": str(src),
            "SCITEX_TEST_LOADED_A": None,
            "SCITEX_TEST_LOADED_B": None,
        }
    ):
        load_scitex_notification_env()
        observed = os.environ.get("SCITEX_TEST_LOADED_A")
        # Clean up env vars set by loader
        os.environ.pop("SCITEX_TEST_LOADED_A", None)
        os.environ.pop("SCITEX_TEST_LOADED_B", None)

    # Assert
    assert observed == "value_a"


def test_load_scitex_notification_env_writes_value_b_to_environ(tmp_path):
    """load_scitex_notification_env() injects loaded variables into os.environ."""
    # Arrange
    from scitex_notification._env_loader import load_scitex_notification_env

    src = tmp_path / "notify.src"
    src.write_text(
        textwrap.dedent("""\
            SCITEX_TEST_LOADED_A=value_a
            SCITEX_TEST_LOADED_B=value_b
        """)
    )

    # Act
    with _scoped_env(
        {
            "SCITEX_NOTIFICATION_ENV_SRC": str(src),
            "SCITEX_TEST_LOADED_A": None,
            "SCITEX_TEST_LOADED_B": None,
        }
    ):
        load_scitex_notification_env()
        observed = os.environ.get("SCITEX_TEST_LOADED_B")
        # Clean up env vars set by loader
        os.environ.pop("SCITEX_TEST_LOADED_A", None)
        os.environ.pop("SCITEX_TEST_LOADED_B", None)

    # Assert
    assert observed == "value_b"


# ---------------------------------------------------------------------------
# test_parse_src_file_nonexistent_returns_empty
# ---------------------------------------------------------------------------
def test_parse_src_file_returns_empty_for_missing_file(tmp_path):
    """parse_src_file() returns empty dict for a nonexistent file."""
    # Arrange
    from scitex_notification._env_loader import parse_src_file

    # Act
    result = parse_src_file(tmp_path / "nonexistent.src")

    # Assert
    assert result == {}


# EOF
