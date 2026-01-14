import datetime
from typing import Any, Mapping, Optional, Union

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    BaseCallbackHandler,
    CallbackManagerForLLMRun,
)
from langchain_core.documents import Document
from langchain_core.language_models import FakeListLLM
from langchain_core.language_models.llms import LLM
from langchain_core.retrievers import BaseRetriever

from .database_mock import DatabaseMock

FAKE_TIME = datetime.datetime(2024, 12, 25, 17, 5, 55)


class FakeVectorDB(BaseRetriever):
    """A fake vector database for testing."""

    documents: list[Document]

    def __init__(self, documents):
        """Initialize with a list of documents."""
        super().__init__(documents=documents)
        self.documents = documents

    def _get_relevant_documents(self, query, *, run_manager):
        return self.documents

    async def _aget_relevant_documents(self, query, *, run_manager):
        return self.documents

    async def asimilarity_search(self, query, k=1, **kwargs):
        """Simulate a similarity search."""
        return self.documents[:k]

    def similarity_search_with_relevance_scores(self, query, k=1, **kwargs):
        """Simulate a similarity search."""
        return [(doc, 1.0) for doc in self.documents[:k]]

    def max_marginal_relevance_search(self, query, k=1, fetch_k=20, **kwargs):
        """Simulate a max marginal relevance search."""
        return self.documents[:k]

    def as_retriever(self):
        """Return the vector store as a retriever."""
        return self


class FakeListLLMStructured(LLM):
    """Fake LLM with 'support' for structured output."""

    responses: list[str | dict]
    """List of responses to return in order."""
    # This parameter should be removed from FakeListLLM since
    # it's only used by sub-classes.
    sleep: Optional[float] = None
    """Sleep time in seconds between responses.

    Ignored by FakeListLLM, but used by sub-classes.
    """
    i: int = 0
    """Internally incremented after every model invocation.

    Useful primarily for testing purposes.
    """

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "fake-list"

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Return next response."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        return response

    async def _acall(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Return next response."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        return response

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"responses": self.responses}

    def with_structured_output(
        self, schema: Union[dict, type], **kwargs: Any
    ) -> "FakeListLLMStructured":
        """Mock implementation of with_structured_output for testing.

        Returns self to allow for method chaining.
        """
        return self

    def bind_tools(
        self,
        tools,
        *,
        tool_choice: Optional[Union[str]] = None,
        **kwargs: Any,
    ) -> "FakeListLLMStructured":
        """Bind tools to the model."""
        return self


class BaseBotTest:
    """Base class for testing bots."""

    base_route: str
    default_data = {
        "id": "123",
        "language": "en",
        "chat_history": [],
        "response_preferences": {
            "detail": 1,
            "illustration": 4,
            "language_style": 4,
            "humour": 2,
            "creativity": 1,
            "emojis": 3,
        },
        "llm_purpose": "optimal"
    }

    @pytest.fixture
    def fake_llm(self) -> FakeListLLM:
        """Get the fake LLM for the tests."""
        return FakeListLLMStructured(responses=["This is a fake response."])

    def patch_urls(self, monkeypatch, mocker):
        """Path the URLs to invalid variables."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "testing")
        monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
        monkeypatch.setenv("LANGFUSE_HOST", "https://asdf.invalid")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "some_public_key")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "some_secret_key")
        mocker.patch(
            "langfuse.langchain.CallbackHandler", return_value=BaseCallbackHandler()
        )

    @pytest.fixture
    def app(self, monkeypatch, mocker):
        """A fixture that sets up the app for testing.

        Fixtures are used to set up resources before and after tests
        and are automatically inserted by pytest
        when they are passed as arguments to test functions.
        """
        self.patch_urls(monkeypatch, mocker)
        from api import app as fastapi

        return fastapi

    @pytest.fixture
    def client(self, app):
        """A fixture that sets up the test client."""
        return TestClient(app)

    def mock_db(self, mocker):
        """Replace the database with a mock for testing."""
        mocked_db = DatabaseMock()
        mocker.patch(
            "bots.base_bot.BaseBot.get_db",
            return_value=mocked_db,
        )
        mocker.patch(
            "bots.base_bot.BaseBot.ainit_db_connection",
            return_value=None,
        )
        mocker.patch(
            "framework.config.get_db",
            return_value=mocked_db,
        )

    def mock_datetime_now(self, monkeypatch, mocker):
        """Patch datetime to return a fixed time."""

        class mydatetime(datetime.datetime):
            @classmethod
            def now(cls):
                return FAKE_TIME

        monkeypatch.setattr(datetime, "datetime", mydatetime)
        mocker.patch("datetime.datetime", return_value=mydatetime)

    def mock_llms(self, mocker, llm):
        """Mock the LLMs used in the bot."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=llm)
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=llm)

    def mock_litellm_llm(self, mocker, llm):
        """Mock the LiteLLM used in the bot."""
        mocker.patch("framework.llm.litellm.LiteLLM.llm", return_value=llm)

    def mock_litellm_chatopenai(self, mocker, llm):
        """Mock the LiteLLM chat openai used in the bot."""
        mocker.patch("framework.llm.litellm.LiteLLM.llm_chatopenai", return_value=llm)

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

    def test_startchat_greeting(self, client, mocker):
        """Test default '/' endpoint for every bot."""
        self.mock_db(mocker)
        self.mock_db(mocker)
        response = self.post_request("/", self.default_data, client)
        assert response.status_code == 200
        assert len(response.json()["messages"]) > 0

    def test_has_get_modules_endpoint(self, client, mocker):
        """Test that the bot has a '/modules' endpoint."""
        self.mock_db(mocker)
        self.mock_db(mocker)
        response = self.get_request("/modules", client)
        assert response.status_code == 200
