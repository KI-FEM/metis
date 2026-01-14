import sys
from pathlib import Path

from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
import pytest

from ..base_bot_test import BaseBotTest, FakeVectorDB
from ..data import (
    localized_title_prompt_output,
    open_conversation_data_grumci,
)
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from bots.grumci.localization import localization
from bots.grumci.localization.base_local import BaseLocalization
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message
from framework.api_types.response_preferences import ResponsePreferences


class TestGrumciBot(BaseBotTest):
    """Test class for the Grumci Bot grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "grumci"

    def test_localizations(self):
        """Test that the localizations are correctly set up."""
        base_localization_properties = vars(BaseLocalization).keys()
        for locale in [LocaleType.DE, LocaleType.EN]:
            assert locale in localization, f"Missing {locale} localization"
            for prop in base_localization_properties:
                if not prop.startswith("__"):
                    assert prop in localization[locale], (
                        f"Missing {prop} in {locale} localization"
                    )

    def test_default_endpoint(self, client):
        """Test '/' endpoint when starting a fresh chat.

        It sends a POST request to '/' with an empty JSON payload.
        This should return a welcome message and the option to select a learning type.
        """
        response = self.post_request(
            "/", {**self.default_data, "language": "de"}, client
        )
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "messages": [
                {
                    "buttons": [],
                    "content": "Hallo 👋 Ich bin _Gery_ und "
                    "ich bin hier, um dir dabei zu helfen, Konzepte in "
                    "der Mensch-Computer-Interaktion zu lernen und zu "
                    "verstehen. Ich freue mich darauf, dein Assistent "
                    "und Begleiter auf dieser Reise zu sein. \n"
                    "Wo sollen wir anfangen? 🤗",
                    "meta_information": {
                        "llm_model": None,
                        "citations": None,
                        "sources": None,
                        "source": "init_chat",
                    },
                    "thoughts": None,
                    "type": "assistant",
                }
            ],
            "storage": {},
            "error": None,
        }

    def test_open_conversation(self, client, fake_llm, mocker):
        """Test '/message' endpoint."""
        self.mock_db(mocker)
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=fake_llm
        )
        mocker.patch("bots.grumci.grumci_bot.multi_language_retriever", return_value=[])

        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\n{{module}}\n{{context}}",
                    "role": "system",
                },
            ],
            name="title-en",
        ).add_prompt(
            prompt=[
                {"content": "retriever prompt", "role": "system"},
            ],
            name="st-module-retriever-query-en",
            prompt_type="chat",
        ).patch(mocker)
        response = self.post_request("/message", open_conversation_data_grumci, client)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["content"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 0

    def test_get_localized_langfuse_prompt(self, mocker, monkeypatch):
        """Test the get_localized_langfuse_prompt function."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(content="Hi How are you?", type="assistant", timestamp="0"),
            Message(content="I am good. How about you?", type="user", timestamp="1"),
        ]
        pref = ResponsePreferences(
            detail=1, illustration=4, language_style=4, humour=2, creativity=1, emojis=3
        )

        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{grumci_role}}\n{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\nHi",
                    "role": "system",
                },
                {"content": "Hello {{name}}.", "role": "user"},
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the competence description.",
            name="grumci-description-en",
            prompt_type="text",
        ).patch(mocker)

        from bots.grumci.grumci_bot import get_localized_langfuse_prompt

        assert (
            get_localized_langfuse_prompt(
                "title", LocaleType.EN, pref, chat=chat
            ).format(name="StudyBot")
            == localized_title_prompt_output
        )

    @pytest.mark.asyncio
    async def test_update_chain(self, mocker):
        """Test the update_chain method."""
        from langchain_core.runnables import RunnableSerializable

        from bots.grumci.grumci_bot import update_chain

        self.mock_db(mocker)
        prompt = PromptTemplate(name="asdf", template="asdf", input_variables=[])
        runnable = await update_chain(prompt, LocaleType.DE, 0.5, 200)

        assert isinstance(runnable, RunnableSerializable) is True
