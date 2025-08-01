import pytest

"""
Example test file for mcp_pr_recommender.
"""


class TestExample:
    """Example test class."""

    @pytest.mark.unit
    def test_example(self):
        """Example test method."""
        assert True

    @pytest.mark.unit
    def test_list_operations(self):
        """Test list operations."""
        items = ["feature", "bugfix", "docs"]
        assert len(items) == 3
        assert "feature" in items
