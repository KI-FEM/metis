import datetime
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.runnables import RunnableSerializable

from ..base_bot_test import BaseBotTest, FakeVectorDB
from ..data import open_conversation_data
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message, MessageType
from framework.api_types.response_preferences import ResponsePreferences
from framework.router import Router


class TestCitationBot(BaseBotTest):
    """Test class for the CitationBot grouping tests together."""

    @pytest.fixture
    def app(self, monkeypatch, mocker):
        """Set up the Flask app for the tests."""
        self.patch_urls(monkeypatch, mocker)
        return FastAPI()

    @pytest.fixture
    def client(self, app):
        """Set up the test client for the router."""
        return TestClient(app)

    @pytest.fixture
    def router(self, app):
        """Set up the router for the tests."""
        return Router(app)

    @pytest.fixture
    def citation_bot(self, router):
        """Get the original citation_bot bot for the tests."""
        from bots.citation.citation_bot import citation_bot

        router.register_bot(citation_bot)
        return citation_bot

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "citation"

    def test_startchat_greeting(self, client, mocker, citation_bot):
        """Test default '/' endpoint for every bot."""
        super().test_startchat_greeting(client, mocker)

    def test_has_get_modules_endpoint(self, client, mocker, citation_bot):
        """Test that the bot has a '/modules' endpoint."""
        super().test_has_get_modules_endpoint(client, mocker)

    def test_default_endpoint(self, client, citation_bot):
        """Test '/' endpoint when starting a fresh chat.

        It sends a POST request to '/' with an empty JSON payload.
        This should return a welcome message and the option to select a learning type.
        """
        response = self.post_request("/", self.default_data, client)
        assert response.status_code == 200
        response_json = response.json()
        assert response_json == {
            "messages": [
                {
                    "content": (
                        "Hi! I'm your writing coach –"
                        " here to support you, not to judge. "
                        "Writing can be messy and hard, and that's totally okay."
                        "Let's take the next step together.\n\n"
                        "First, where are you today with your writing?"
                    ),
                    "type": "assistant",
                    "buttons": [
                        {
                            "callback": {
                                "data": {"status": "getting_started"},
                                "endpoint": "writing_status",
                            },
                            "chat_message": "I'm just getting started",
                            "label": "I'm just getting started",
                            "store": {},
                        },
                        {
                            "callback": {
                                "data": {"status": "stuck"},
                                "endpoint": "writing_status",
                            },
                            "chat_message": "I'm stuck somewhere",
                            "label": "I'm stuck somewhere",
                            "store": {},
                        },
                        {
                            "callback": {
                                "data": {"status": "need_feedback"},
                                "endpoint": "writing_status",
                            },
                            "chat_message": "I have something written, but need feedback",
                            "label": "I have something written, but need feedback",
                            "store": {},
                        },
                        {
                            "callback": {
                                "data": {"status": "need_motivation"},
                                "endpoint": "writing_status",
                            },
                            "chat_message": "I just need motivation",
                            "label": "I just need motivation",
                            "store": {},
                        },
                    ],
                    "meta_information": {
                        "sources": None,
                        "llm_model": None,
                        "citations": None,
                        "source": "init_chat",
                    },
                    "thoughts": None,
                }
            ],
            "storage": {},
            "instructions": [],
            "error": None,
        }

    def test_update_title(self, client, mocker, fake_llm, citation_bot):
        """Test the update title endpoint."""
        self.mock_llms(mocker, fake_llm)
        self.mock_db(mocker)
        PromptPatcher().add_prompt(
            prompt=[{"content": "Generate title!", "role": "system"}],
            name="title-en",
            prompt_type="chat",
        ).patch(mocker)

        response = self.post_request("/title", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == {"title": "This is a fake response.", "error": None}

    def test_select_topic(self, client, citation_bot):
        """Test '/select_topic' endpoint when selecting a topic.

        It sends a POST request to '/select_topic' with a JSON payload containing
        the selected topic. This should return a message to select a topic.
        """
        response = self.post_request("/select_topic", self.default_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "messages": [
                {
                    "content": (
                        "I'll help you with scientific writing! Let's start with a quick check-in.\n\n"
                        "First, where are you today with your writing?"
                    ),
                    "type": "assistant",
                    "buttons": [
                        {
                            "chat_message": "I'm just getting started",
                            "label": "I'm just getting started",
                            "callback": {
                                "endpoint": "writing_status",
                                "data": {"status": "getting_started"},
                            },
                            "store": {},
                        },
                        {
                            "chat_message": "I'm stuck somewhere",
                            "label": "I'm stuck somewhere",
                            "callback": {
                                "endpoint": "writing_status",
                                "data": {"status": "stuck"},
                            },
                            "store": {},
                        },
                        {
                            "chat_message": "I have something written, but need feedback",
                            "label": "I have something written, but need feedback",
                            "callback": {
                                "endpoint": "writing_status",
                                "data": {"status": "need_feedback"},
                            },
                            "store": {},
                        },
                        {
                            "chat_message": "I just need motivation",
                            "label": "I just need motivation",
                            "callback": {
                                "endpoint": "writing_status",
                                "data": {"status": "need_motivation"},
                            },
                            "store": {},
                        },
                    ],
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                }
            ],
            "storage": {},
            "instructions": [],
            "error": None,
        }

    def patch_create_chain(self, mocker):
        """Patch the create_chain function with the previously set prompts."""
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{citation_role}}\n{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\nHi",
                    "role": "system",
                }
            ],
            name="citation-chat-en",
        ).add_prompt(
            prompt="This is the citation description.",
            name="citation-description-en",
            prompt_type="text",
        ).patch(mocker)

    def test_open_conversation(self, client, mocker, fake_llm, citation_bot):
        """Test method for the '/message' endpoint when sending a message.

        It sends a POST request to '/message' with a JSON payload containing a message.
        This should return a response message.
        """
        self.mock_db(mocker)
        self.mock_llms(mocker, fake_llm)
        self.patch_create_chain(mocker)

        mocker.patch(
            "bots.citation.citation_bot.CitationBot.get_vector_store",
            return_value=FakeVectorDB([Document("bla bla bla", id="1")]),
        )
        response = self.post_request(
            "/message",
            {
                **open_conversation_data,
                "storage": {
                    "selected_competence": "Research",
                    "selected_topic": "Scientific work",
                },
            },
            client,
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["content"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 1

    @pytest.mark.asyncio
    async def test_update_chain(self, mocker, monkeypatch, citation_bot):
        """Test the update_chain method."""
        from bots.citation.citation_bot import update_chain

        self.mock_db(mocker)
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(
                content="Hi How are you?",
                type=MessageType.ASSISTANT,
                timestamp="0"
            ),
            Message(
                content="I am good. How about you?",
                type=MessageType.USER,
                timestamp="1"
            ),
        ]
        pref = ResponsePreferences(
            detail=1, illustration=1, language_style=1, humour=1, creativity=1, emojis=1
        )

        self.patch_create_chain(mocker)
        mocker.patch(
            "bots.citation.citation_bot.load_module_db", return_value=mocker.MagicMock()
        )
        chain = await update_chain(pref, LocaleType.EN, chat)
        assert isinstance(chain, RunnableSerializable)
