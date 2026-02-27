import sys
from pathlib import Path

from langchain.prompts import PromptTemplate

from ..base_bot_test import BaseBotTest
from ..data import (
    localized_title_prompt_output_st_buddy,
    open_conversation_data_st_buddy,
)
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from framework.api_types.learning_type import LearningTypes
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message


class TestStBuddy(BaseBotTest):
    """Test class for the ST Buddy grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "st"

    def test_default_endpoint(self, client):
        """Test '/' endpoint when starting a fresh chat.

        It sends a POST request to '/' with an empty JSON payload.
        This should return a welcome message and the option to select a learning type.
        """
        response = self.post_request(
            "/", 
            {**self.default_data, "language": "de"}, 
            client)
        assert response.status_code == 200
        assert response.json() == {
            'instructions': [],
            'messages': [
                {
                    'buttons': [],
                    'message': 'Hallo 👋 Ich bin der _StBuddy_ und '
                                'ich bin hier, um dir dabei zu helfen, Konzepte in '
                                'der Software-Technologie zu lernen und zu '
                                'verstehen. Ich freue mich darauf, dein Assistent '
                                'und Begleiter auf dieser Reise zu sein. \n'
                                'Wo sollen wir anfangen? 🤗',
                    'meta_information': {'llm_model': None, 'citations': None, 'sources': None},
                    'thoughts': None,
                    'sender': 'assistant'
                }
            ],
           'storage': {}
        }

    def test_default_endpoint_english(self, client):
        """Test '/' endpoint when starting a fresh chat.

        It sends a POST request to '/' with an empty JSON payload.
        This should return a welcome message and the option to select a learning type.
        """
        response = self.post_request(
            "/",
            {**self.default_data, "language": "en"},
            client)
        assert response.status_code == 200
        assert response.json() == {
            'instructions': [],
            'messages': [
                {
                    'buttons': [],
                    'message': "Hello 👋 I am _StBuddy_ and I'm "
                                'here to help you learn and understand concepts in '
                                "software technology. I'm excited to be your "
                                'assistant and guide throughout this journey. \n'
                                'Where shall we start? 🤗',
                    'meta_information': {'llm_model': None, 'citations': None, 'sources': None},
                    'thoughts': None,
                    'sender': 'assistant'
                }
            ],
            'storage': {}
        }

    def test_startchat_previously_learned_wrong_learning_type(self, client):
        """Test '/' endpoint when starting a chat with a wrong learning type."""
        response = self.post_request("/", {"learning_type_id": "asdf"}, client)
        assert response.status_code == 422

    def test_select_module(self, client, fake_llm, mocker):
        """Test '/select_module' endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{st_role}}\n{{learning_type_description}}\n", 
                    "role": "system"
                },
                {
                    "content": "{{user_message}}",
                    "role": "user"
                }
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the st description.",
            name="st-description-en",
            prompt_type="text"
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text"
        ).patch(mocker)

        response = self.post_request("/select_module", {
            **self.default_data,
            "storage": {
                "value": "content"
            }
        }, client)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 0

    def test_open_conversation(self, client, fake_llm, mocker):
        """Test '/message' endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=fake_llm)

        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{st_role}}\n{{learning_type_description}}\n{{module}}\n{{context}}",
                    "role": "system"
                },
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the st description.",
            name="st-description-en",
            prompt_type="text"
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text"
        ).add_prompt(
            prompt=[
                {
                    "content": "retriever prompt",
                    "role": "system"
                },
            ],
            name="st-module-retriever-query-en",
            prompt_type="chat"
        ).patch(mocker)
        response = self.post_request("/message", open_conversation_data_st_buddy, client)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 3

    def test_get_localized_langfuse_prompt(self, mocker, monkeypatch):
        """Test the get_localized_langfuse_prompt function."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(message="Hi How are you?", sender="assistant", timestamp="0"),
            Message(message="I am good. How about you?", sender="user", timestamp="1")
        ]
        learning_type = LearningTypes.FEELING.value
        
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{st_role}}\n{{learning_type_description}}\nHi", 
                    "role": "system"
                },
                {
                    "content": "Hello {{name}}.", 
                    "role": "user"
                }
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the st description.",
            name="st-description-en",
            prompt_type="text"
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text"
        ).patch(mocker)
        
        from bots.st.st_buddy import get_localized_langfuse_prompt
        assert get_localized_langfuse_prompt(
            "title",
            LocaleType.EN,
            learning_type,
            chat=chat
        ).format(name="StBuddy") == localized_title_prompt_output_st_buddy
        
    def test_update_chain(self):
        """Test the update_chain method."""
        from langchain_core.runnables import RunnableSerializable

        from bots.st.st_buddy import update_chain
        prompt = PromptTemplate(name="asdf", template="asdf", input_variables=[])
        runnable = update_chain(prompt, LocaleType.DE, 0.5, 200)
        
        assert isinstance(runnable, RunnableSerializable) is True
