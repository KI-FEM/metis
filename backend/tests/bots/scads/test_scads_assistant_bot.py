import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))
from bots.scads.scads_assistant_bot import ScaDSAssistantBot
from framework.api_types.localized_string import LocalizedString


class TestScaDSAssistantBot:
    """Test class for the ScaDS Assistant Bot."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up environment variables for testing."""
        monkeypatch.setenv("LITELLM_URL", "http://test-url.com")
        monkeypatch.setenv("LITELLM_KEY", "test-key")

    @pytest.fixture
    def test_bot(self, mock_env):
        """Create a test bot instance."""
        return ScaDSAssistantBot(
            model_id="test-assistant",
            name=LocalizedString("Test Assistant", "Test Assistent"),
            short_description=LocalizedString("Test bot", "Test Bot"),
            long_description=LocalizedString(
                "I am a test assistant", "Ich bin ein Test-Assistent"
            ),
            color="#FF0000",
            priority=5,
        )

    def test_bot_initialization(self, test_bot):
        """Test that bot initializes with correct attributes."""
        assert test_bot.model_id == "test-assistant"
        assert test_bot.id == "scads_test_assistant"
        assert test_bot.name.en() == "Test Assistant"
        assert test_bot.color == "#FF0000"
        assert test_bot.priority == 5
        assert test_bot.tag == "ScaDS.AI"

    def test_get_scads_config(self, test_bot):
        """Test that ScaDS configuration is retrieved correctly."""
        base_url, api_key = test_bot._get_scads_config()
        
        assert base_url == "http://test-url.com/v1/scads-assistants"
        assert api_key == "test-key"

    def test_get_scads_config_missing_url(self, monkeypatch):
        """Test that missing LITELLM_URL raises error."""
        monkeypatch.delenv("LITELLM_URL", raising=False)
        monkeypatch.setenv("LITELLM_KEY", "test-key")
        
        bot = ScaDSAssistantBot(
            model_id="test",
            name=LocalizedString("Test", "Test"),
            short_description=LocalizedString("Test", "Test"),
            long_description=LocalizedString("Test", "Test"),
        )
        
        with pytest.raises(ValueError, match="LITELLM_URL"):
            bot._get_scads_config()

    def test_get_modules_returns_empty_list(self, test_bot):
        """Test that ScaDS bots don't have modules."""
        modules = test_bot.get_modules()
        assert modules == []

    def test_bot_has_scads_tag(self, test_bot):
        """Test that bot is tagged as ScaDS.AI."""
        assert test_bot.tag == "ScaDS.AI"

    def test_bot_router_prefix(self, test_bot):
        """Test that bot router has correct prefix."""
        assert test_bot.router.prefix == "/topic/scads_test_assistant"
