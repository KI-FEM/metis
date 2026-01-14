"""Tests for the ScaDS Assistant Factory."""

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))
from bots.scads.scads_assistant_bot import ScaDSAssistantBot
from bots.scads.scads_factory import ScaDSAssistantFactory


class TestScaDSAssistantFactory:
    """Test class for the ScaDS Assistant Factory."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv("LITELLM_URL", "http://test-url.com")
        monkeypatch.setenv("LITELLM_KEY", "test-key")

    def test_factory_initialization(self, mock_env):
        """Test that factory initializes correctly."""
        factory = ScaDSAssistantFactory()
        assert factory is not None
        assert factory._cached_bots is None

    def test_get_base_url(self, mock_env):
        """Test that base URL is correctly constructed."""
        factory = ScaDSAssistantFactory()
        base_url = factory._get_base_url()
        assert base_url == "http://test-url.com/v1/scads-assistants"

    def test_get_metadata_for_known_assistant(self, mock_env):
        """Test metadata retrieval for known assistants."""
        factory = ScaDSAssistantFactory()
        
        # HPC-Buddy is a known assistant with predefined metadata
        metadata = factory._get_metadata_for_model("HPC-Buddy")
        
        assert "name" in metadata
        assert "short_description" in metadata
        assert "long_description" in metadata
        assert metadata["name"].en() == "HPC Buddy"

    def test_get_metadata_for_unknown_assistant_uses_defaults(self, mock_env):
        """Test that unknown assistants get default metadata."""
        factory = ScaDSAssistantFactory()
        
        # Unknown assistant should get DEFAULT_METADATA
        metadata = factory._get_metadata_for_model("unknown-bot")
        
        assert "color" in metadata
        assert "priority" in metadata
        assert metadata["color"] == "#63a44b"  # DEFAULT_METADATA color
        assert metadata["priority"] == 0  # DEFAULT_METADATA priority

    def test_clear_cache(self, mock_env):
        """Test that cache can be cleared."""
        factory = ScaDSAssistantFactory()
        # Simulate cached bots without actually creating them
        factory._cached_bots = ["mock_bot"]

        factory.clear_cache()

        assert factory._cached_bots is None
