import sys
from pathlib import Path
from typing import Any, Union

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import FakeListLLM

sys.path.append(str(Path(Path(__file__).parent.parent.parent / "src")))
    
class FakeListLLMStructured(FakeListLLM):
    """Fake LLM with 'support' for structured output."""
    def with_structured_output(
        self, schema: Union[dict, type], **kwargs: Any
    ) -> 'FakeListLLMStructured':
        """Mock implementation of with_structured_output for testing.
        
        Returns self to allow for method chaining.
        """
        return self


class BaseBotTest:
    """Base class for testing bots."""

    base_route: str
    default_data = {"language": "en", "learning_type_id": "FEELING", "chat_history": []}

    @pytest.fixture
    def fake_llm(self) -> FakeListLLM:
        """Get the fake LLM for the tests."""
        return FakeListLLMStructured(responses=["This is a fake response."])

    @pytest.fixture
    def app(self, monkeypatch, mocker):
        """A fixture that sets up the app for testing.

        Fixtures are used to set up resources before and after tests
        and are automatically inserted by pytest
        when they are passed as arguments to test functions.
        """
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "testing")
        monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
        mocker.patch("langfuse.callback.CallbackHandler.run_inline", return_value=None)
        from api import app as fastapi

        return fastapi

    @pytest.fixture
    def client(self, app):
        """A fixture that sets up the test client."""
        return TestClient(app)

    def post_request(self, route, data, client):
        """A helper function to send a POST request to the bot."""
        if self.base_route is None:
            raise ValueError("Base route is not set.")
        return client.post(f"/topic/{self.base_route}{route}", json=data)

    def get_request(self, route, client):
        """A helper function to send a GET request to the bot."""
        if self.base_route is None:
            raise ValueError("Base route is not set.")
        return client.get(f"/topic/{self.base_route}{route}")

    def put_request(self, route, data, client):
        """A helper function to send a PUT request to the bot."""
        if self.base_route is None:
            raise ValueError("Base route is not set.")
        return client.put(f"/topic/{self.base_route}{route}", json=data)

    def test_startchat_greeting(self, client):
        """Test default '/' endpoint for every bot."""
        response = self.post_request("/", self.default_data, client)
        assert response.status_code == 200
        assert len(response.json()["messages"]) > 0
        
    def test_has_get_modules_endpoint(self, client):
        """Test that the bot has a '/modules' endpoint."""
        response = self.get_request("/modules", client)
        assert response.status_code == 200
