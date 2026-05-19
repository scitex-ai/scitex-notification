#!/usr/bin/env python3
"""Smoke tests for scitex_notification._mcp.tool_schemas."""

import pytest

from scitex_notification._mcp import tool_schemas


def _get_schemas():
    schemas = tool_schemas.get_tool_schemas()
    out = []
    for s in schemas:
        if hasattr(s, "model_dump"):
            out.append(s.model_dump())
        elif isinstance(s, dict):
            out.append(s)
        else:
            out.append(
                {
                    "name": getattr(s, "name", None),
                    "description": getattr(s, "description", None),
                }
            )
    return out


class TestToolSchemas:
    def test_returns_a_list_type(self):
        # Arrange
        # (helper does the work)
        # Act
        schemas = _get_schemas()

        # Assert
        assert isinstance(schemas, list)

    def test_returns_non_empty_list_of_schemas(self):
        # Arrange
        # (helper does the work)
        # Act
        schemas = _get_schemas()

        # Assert
        assert len(schemas) > 0

    def test_every_tool_has_a_name_string(self):
        # Arrange
        schemas = _get_schemas()

        # Act
        invalid = [s for s in schemas if not (s["name"] and isinstance(s["name"], str))]

        # Assert
        assert invalid == []

    def test_every_tool_has_a_description_string(self):
        # Arrange
        schemas = _get_schemas()

        # Act
        invalid = [
            s
            for s in schemas
            if not (s["description"] and isinstance(s["description"], str))
        ]

        # Assert
        assert invalid == []

    def test_tool_names_are_unique_across_schemas(self):
        # Arrange
        schemas = _get_schemas()

        # Act
        names = [s["name"] for s in schemas]
        unique_count = len(set(names))

        # Assert
        assert len(names) == unique_count


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])

# EOF
