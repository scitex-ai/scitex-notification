#!/usr/bin/env python3
"""Tests for scitex_notification._cli._helpers."""

import json

import click
import pytest

from scitex_notification._cli._helpers import (
    emit_result,
    group_to_json,
    print_help_recursive,
)


@click.group()
def root():
    """Root group."""


@root.command()
def hello():
    """Say hello."""


class TestPrintHelpRecursive:
    def test_emits_root_group_name(self, capsys):
        # Arrange
        ctx = click.Context(root)

        # Act
        print_help_recursive(ctx, root)
        out = capsys.readouterr().out

        # Assert
        assert "root" in out

    def test_emits_subcommand_name(self, capsys):
        # Arrange
        ctx = click.Context(root)

        # Act
        print_help_recursive(ctx, root)
        out = capsys.readouterr().out

        # Assert
        assert "hello" in out


class TestGroupToJson:
    def test_emits_group_name_in_json(self, capsys):
        # Arrange
        ctx = click.Context(root)

        # Act
        group_to_json(ctx, root)
        out = capsys.readouterr().out
        data = json.loads(out)

        # Assert
        assert data["name"] == "root"

    def test_emits_subcommand_in_json(self, capsys):
        # Arrange
        ctx = click.Context(root)

        # Act
        group_to_json(ctx, root)
        out = capsys.readouterr().out
        data = json.loads(out)

        # Assert
        assert "hello" in data["subcommands"]


class TestEmitResult:
    def test_writes_dict_payload_to_stdout(self, capsys):
        # Arrange
        payload = {"x": 1}

        # Act
        emit_result(payload, success=True)
        out = capsys.readouterr().out
        # Output may be wrapped in scitex_dev Result envelope OR plain JSON
        # — verify the payload key landed somewhere.
        contains_key = '"x"' in out or "'x'" in out

        # Assert
        assert contains_key


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
