import json
import sys
from pathlib import Path
from typing import Any, Optional, TypedDict

from langchain_core.language_models import FakeListLLM

from ..base_bot_test import BaseBotTest, FakeListLLMStructured
from ..data import (
    localized_title_prompt_output,
    open_conversation_data,
    submit_test_data,
    suggested_questions_data,
)
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from bots.base_bot import ResponseGenerationData
from bots.study.localization import localization
from bots.study.localization.base_local import BaseLocalization
from framework.api_types.learning_type import LearningTypes
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message, RequestModel, Sender
from framework.api_types.response_format import Source


class TestStudyCompetenceBot(BaseBotTest):
    """Test class for the StudyCompetenceBot grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "study_competence"

    def test_localizations(self):
        """Test that the localizations are correctly set up."""
        base_localization_properties = vars(BaseLocalization).keys()
        for locale in [LocaleType.DE, LocaleType.EN]:
            assert locale in localization, f"Missing {locale} localization"
            for prop in base_localization_properties:
                if not prop.startswith("__"):
                    assert (
                        prop in localization[locale]
                    ), f"Missing {prop} in {locale} localization"

    def test_get_modules(self, client):
        """Test '/modules' endpoint."""
        response = self.get_request("/modules", client)
        assert response.status_code == 200
        assert response.json() == {
            "modules": [
                {"id": "resilience", "title": {"de": "Resilienz", "en": "Resilience"}},
                {
                    "id": "self_efficacy",
                    "title": {"de": "Selbstwirksamkeit", "en": "Self-Efficacy"},
                },
                {
                    "id": "learning_strategies",
                    "title": {"de": "Lernstrategien", "en": "Learning Strategies"},
                },
            ]
        }

    def test_default_endpoint(self, client):
        """Test '/' endpoint when starting a fresh chat."""
        response = self.post_request(
            "/", {**self.default_data, "language": "de"}, client
        )
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {},
            "messages": [
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Hallo 👋 Ich bin der _Studienkompetenz Bot_. Ich bin hier, um dir "
                        "bei deinen studienbezogenen Fragen zu helfen. 🧑‍🎓 Ich kann dir "
                        "verschiedene Kompetenzen beibringen, dich auf eine bevorstehende "
                        "Prüfung vorbereiten oder einfach über ein Problem sprechen, mit dem "
                        "du aktuell konfrontiert bist. \nWie kann ich dir heute helfen? 🤗"
                    ),
                    "buttons": [],
                },
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Wähle ein Thema aus, über das du mehr erfahren möchtest. Anschließend "
                        "gebe ich dir eine Übersicht über das Thema und wir können tiefer in "
                        "die Details eintauchen. "
                    ),
                    "buttons": [
                        {
                            "label": "Resilienz",
                            "chat_message": "Ich möchte mehr über Resilienz lernen.",
                            "callback": {
                                "endpoint": "select_module",
                                "data": {"selected_module": "resilience"},
                            },
                            "store": {"selected_module": "resilience"},
                        },
                        {
                            "label": "Selbstwirksamkeit",
                            "chat_message": "Ich möchte mehr über Selbstwirksamkeit lernen.",
                            "callback": {
                                "endpoint": "select_module",
                                "data": {"selected_module": "self_efficacy"},
                            },
                            "store": {"selected_module": "self_efficacy"},
                        },
                        {
                            "callback": {
                                "data": {
                                    "selected_module": "learning_strategies",
                                },
                                "endpoint": "select_module",
                            },
                            "chat_message": "Ich möchte mehr über Lernstrategien lernen.",
                            "label": "Lernstrategien",
                            "store": {
                                "selected_module": "learning_strategies",
                            },
                        },
                    ],
                },
            ],
        }

    def test_default_endpoint_english(self, client):
        """Test '/' endpoint when starting a fresh chat."""
        response = self.post_request("/", self.default_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {},
            "messages": [
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Hello 👋 I am _Study Competence Bot_. I am here to assist you with "
                        "your study-related issues. 🧑‍🎓 I can teach you about various skills"
                        ", prepare for an upcoming exam or just talk about a current issue "
                        "you are facing. \nHow can I help you today? 🤗"
                    ),
                    "buttons": [],
                },
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Select a topic you would like to learn more about. I will then give "
                        "you an overview of the topic and we can dive deeper into the details."
                    ),
                    "buttons": [
                        {
                            "label": "Resilience",
                            "chat_message": "I would like to learn more about Resilience, please.",
                            "callback": {
                                "endpoint": "select_module",
                                "data": {"selected_module": "resilience"},
                            },
                            "store": {"selected_module": "resilience"},
                        },
                        {
                            "label": "Self-Efficacy",
                            "chat_message": "I would like to learn more about Self-Efficacy, please.",
                            "callback": {
                                "endpoint": "select_module",
                                "data": {"selected_module": "self_efficacy"},
                            },
                            "store": {"selected_module": "self_efficacy"},
                        },
                        {
                            "callback": {
                                "data": {
                                    "selected_module": "learning_strategies",
                                },
                                "endpoint": "select_module",
                            },
                            "chat_message": "I would like to learn more about Learning Strategies, please.",
                            "label": "Learning Strategies",
                            "store": {
                                "selected_module": "learning_strategies",
                            },
                        },
                    ],
                },
            ],
        }

    def test_suggested_questions(self, client):
        """Test '/suggested_questions' endpoint."""
        response = self.post_request(
            "/inspiration",
            {
                "storage": {"selected_module": "learning_strategies"},
                **self.default_data,
            },
            client,
        )

        assert response.status_code == 200
        assert response.json() == suggested_questions_data

    def test_get_localized_langfuse_prompt(self, mocker, monkeypatch):
        """Test the get_localized_langfuse_prompt function."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(message="Hi How are you?", sender=Sender.ASSISTANT, timestamp="0"),
            Message(
                message="I am good. How about you?", sender=Sender.USER, timestamp="1"
            ),
        ]
        learning_type = LearningTypes.FEELING.value

        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{competence_role}}\n{{learning_type_description}}\nHi",
                    "role": "system",
                },
                {"content": "Hello {{name}}.", "role": "user"},
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the competence description.",
            name="competence-description-en",
            prompt_type="text",
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)

        from bots.study.study_competence_bot import get_localized_langfuse_prompt

        assert (
            get_localized_langfuse_prompt(
                "title", LocaleType.EN, learning_type, chat=chat
            ).format(name="StudyBot")
            == localized_title_prompt_output
        )

    def test_questions_for_all_modules(self):
        """Test that all topics have example questions for all modules."""
        from bots.study.helpers.data_structure import structure

        for topic in structure["topics"]:
            for module_name in structure["topics"][topic]["modules"]:
                module = structure["topics"][topic]["modules"][module_name]
                if "submodules" in module:
                    submodules = module["submodules"]
                    for submodule in submodules:
                        assert "example_questions" in submodules[submodule]
                else:
                    assert "example_questions" in module

    def test_update_title(self, client, mocker, fake_llm):
        """Test the update title endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[{"content": "Generate title!", "role": "system"}],
            name="title-en",
        ).patch(mocker)
        response = self.post_request("/title", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == {"title": "This is a fake response."}

    def test_select_module(self, client, fake_llm, mocker):
        """Test '/select_module' endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt_type="text",
            name="competence-introduction-summarization-en",
            prompt="Give me documents.",
        ).add_prompt(
            name="competence-introduction-en",
            prompt=[
                {
                    "content": "{{competence_role}}\n{{learning_type_description}}\n{{topic}}\n{{current_level}}\n{{previous_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{summary}}\n{{context}}",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the competence description.",
            name="competence-description-en",
            prompt_type="text",
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)

        response = self.post_request(
            "/select_module",
            {**self.default_data, "storage": {"selected_module": "resilience"}},
            client,
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 4

    def patch_chat_prompts(self, mocker):
        """Patch the chat prompts for testing."""
        PromptPatcher().add_prompt(
            name="competence-open-conversation-en",
            prompt=[
                {
                    "content": "{{competence_role}}\n{{learning_type_description}}\n{{topic}}\n{{includes_summary}}\n{{current_level}}\n{{previous_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{context}}",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the competence description.",
            name="competence-description-en",
            prompt_type="text",
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)

    def test_open_conversation(self, client, fake_llm, mocker):
        """Test '/message' endpoint."""

        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        from langchain_core.documents import Document
        async def mock_retrieve(*args, **kwargs):
            return [Document(page_content="This is a fake document.", metadata={"source": "asdf"})] * 4

        mocker.patch(
            "bots.study.study_competence_bot.auto_retriever", new=mock_retrieve
        )

        def return_bla(*args, **kwargs):
            """Return a fake response for the LLM."""
            return {
                "answer": "This is a fake response [source_id: 1].",
                "citations": [1],
            }

        mocker.patch(
            "langchain_core.runnables.base.RunnableBindingBase.ainvoke",
            side_effect=return_bla,
        )
        self.patch_chat_prompts(mocker)
        response = self.post_request("/message", open_conversation_data, client)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response [source_id: 1]."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 4
        assert response_data["messages"][0]["meta_information"]["citations"][0] == 1

    def test_take_test(self, client, mocker):
        """Test '/quiz' endpoint."""
        quiz = {
            "title": "This is a title",
            "description": "This is a description",
            "questions": [
                {
                    "id": 1,
                    "question": "This is a question",
                    "type": "single-choice",
                    "options": [
                        {"id": 1, "label": "This is an answer", "correct": True}
                    ],
                }
            ],
            "storage": {},
        }

        fake_llm = FakeListLLM(
            responses=[
                json.dumps(quiz),
            ]
        )
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            name="competence-quiz-en",
            prompt=[
                {
                    "content": "{{learning_type_description}}\n{{topic}}\n{{number_of_questions}}\n{{current_level}}\n{{previous_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{context}}",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).add_prompt(
            name="competence-quiz-retrieval-en",
            prompt_type="text",
            prompt="This is the quiz retrieval prompt.",
        ).duplicate().patch(mocker)
        response = self.post_request("/quiz", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == quiz

        # get an invalid quiz from the LLM
        invalid_quiz = {
            "title": "This is a title",
            "questions": [
                {
                    "id": 1,
                    "question": "This is a question",
                    "type": "single-choice",
                    "options": [
                        {"id": 1, "label": "This is an answer", "correct": True}
                    ],
                }
            ],
            "storage": {},
        }
        fake_llm = FakeListLLM(
            responses=[
                json.dumps(invalid_quiz),
            ]
        )
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        response = self.post_request("/quiz", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "title": "ERROR",
            "description": "ERROR",
            "questions": [],
            "storage": {},
        }

    def test_submit_test(self, client, mocker):
        """Test PUT '/quiz' endpoint."""
        feedback = {
            "user_feedback": "This is a feedback",
            "learning_progress": {"resilience": 1},
        }

        fake_llm = FakeListLLM(
            responses=[
                json.dumps(feedback),
            ]
        )
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            name="competence-quiz-conclusion-en",
            prompt=[
                {
                    "content": "{{learning_type_description}}\n{{questions}}\n{{answers}}\n",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)
        response = self.put_request("/quiz", submit_test_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {},
            "messages": [
                {
                    "sender": "user",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "message": "Submitted a quiz.",
                    "thoughts": None,
                    "buttons": [],
                },
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": "llama-3.3",
                    },
                    "message": "This is a feedback",
                    "thoughts": None,
                    "buttons": [],
                },
            ],
        }

    def test_submit_feedback(self, client):
        """Test '/feedback' endpoint."""
        response = self.post_request(
            "/feedback",
            {
                **self.default_data,
                "feedback": {"comment": "I like the bot", "learning_type_rating": 4},
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {},
            "messages": [
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Thank you for your feedback! I am sorry to hear that you are not "
                        "satisfied. Try to change your learning type in the personalisation "
                        "settings and test it out 🙏 "
                    ),
                    "buttons": [],
                },
            ],
        }

        response = self.post_request(
            "/feedback",
            {
                **self.default_data,
                "feedback": {"comment": "I like the bot", "learning_type_rating": 7},
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {},
            "messages": [
                {
                    "sender": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "message": (
                        "Thank you for your feedback! I am glad to hear that you are satisfied "
                        "with my assistance. 😊 "
                    ),
                    "buttons": [],
                },
            ],
        }

    def test_submit_feedback_missing_data(self, client):
        """Test '/feedback' endpoint with missing data."""
        response = self.post_request(
            "/feedback", {"feedback": "I like the bot", "language": "en"}, client
        )
        assert response.status_code == 422

        response = self.post_request(
            "/feedback",
            {
                "feedback": "I like the bot",
                "language": "en",
                "learning_type_fit": "asdf",
            },
            client,
        )
        assert response.status_code == 422

    def test_send_message_streaming(self, client, mocker, fake_llm):
        """Test streaming responses in open_conversation_base."""
        # Mock the LLM to return a predetermined response
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)

        # Mock the prompts
        self.patch_chat_prompts(mocker)

        from langchain_core.runnables import RunnableSerializable

        # Mock the RunnableSerializable to simulate streaming
        mock_chain = mocker.MagicMock(spec=RunnableSerializable)

        async def mock_astream(*args, **kwargs):
            # Simulate tokens being streamed
            tokens = [
                "This ",
                "is ",
                "a ",
                "<think>some thoughts</think>",
                "streamed ",
                "response.",
            ]
            for token in tokens:
                yield token

        mock_chain.astream.side_effect = mock_astream

        # Create a mock OpenConversationModel response
        mock_response = ResponseGenerationData(
            created_chain=mock_chain,
            chain_config={"some": "config"},
            sources={
                0: Source(
                    label="Test Source", chunk="Test content", url="https://test.com"
                )
            },
            llm_model="test-model",
        )

        # Create a request model with necessary parameters
        request_data = {
            "chat_id": "test-chat-id",
            "storage": {"chat_id": "test-chat-id"},
        }
        request = RequestModel(**{**self.default_data, **request_data})

        # Import StudyCompetenceBot and test streaming
        from bots.study.study_competence_bot import StudyCompetenceBot

        bot = StudyCompetenceBot()

        # Collect the streamed response
        stream_generator = bot.stream_message(request, mock_response)
        stream_chunks = []
        import asyncio

        async def collect_stream_chunks():
            async for chunk in stream_generator:
                stream_chunks.append(chunk)

        asyncio.run(collect_stream_chunks())
        # Validate the response format and content
        assert len(stream_chunks) >= 3  # At minimum: metadata, content, and stop chunks

        # First chunk should contain metadata
        first_chunk = stream_chunks[0]
        assert "data: " in first_chunk
        first_chunk_data = json.loads(first_chunk.replace("data: ", "").strip())
        assert first_chunk_data["choices"][0]["delta"]["sender"] == "assistant"
        assert first_chunk_data["choices"][0]["delta"]["llm_model"] == "test-model"

        # Middle chunks should contain content
        content_chunks = stream_chunks[1:-1]
        assert any("streamed" in chunk for chunk in content_chunks)

        # Last chunk should be stop message
        last_chunk = stream_chunks[-1]
        last_chunk_data = json.loads(last_chunk.replace("data: ", "").strip())
        assert last_chunk_data["choices"][0]["finish_reason"] == "stop"

        # Verify we have at least one chunk with thoughts
        thought_chunks = [
            chunk
            for chunk in content_chunks
            if "thoughts"
            in json.loads(chunk.replace("data: ", "").strip())["choices"][0]["delta"]
        ]
        assert len(thought_chunks) > 0

    def test_plan_session(self, client, mocker, fake_llm):
        """Test the '/plan-session' endpoint."""
        # Mock the fake LLM to return a specific JSON response for topics
        topics_response = '{"topics": ["Header 1", "Header 2", "Header 3"]}'
        fake_llm = FakeListLLM(responses=[topics_response])

        # Mock the LLM to return a predetermined response
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)

        # Mock the langfuse prompt
        PromptPatcher().add_prompt(
            name="competence-plan-en",
            prompt=[
                {
                    "content": "{{learning_type_description}}\n{{learning_goals}}\n{{previous_topics}}\n{{available_topics}}",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)

        # Mock get_headers to return some sample headers
        mock_headers = ["Header 1", "Header 2", "Header 3"]
        mocker.patch(
            "bots.study.study_competence_bot.get_headers", return_value=mock_headers
        )

        # Create a request with necessary data
        request_data = {
            "storage": {"selected_module": "resilience", "skill_level": "beginner"}
        }

        # Send the request to the plan-session endpoint
        response = self.post_request(
            "/plan-session", {**self.default_data, **request_data}, client
        )

        # Verify the response
        assert response.status_code == 200
        response_data = response.json()

        # Check that the response has the expected structure
        assert "recommended_topics" in response_data
        assert "recommended_date" in response_data

        # Check that we have exactly 3 recommended topics
        assert len(response_data["recommended_topics"]) == 3

        # Check that the recommended date is a valid ISO format date
        import datetime

        try:
            datetime.date.fromisoformat(response_data["recommended_date"])
            date_valid = True
        except ValueError:
            date_valid = False
        assert date_valid, "Recommended date is not in valid ISO format"

        # Verify the recommended topics match what we expected
        assert set(response_data["recommended_topics"]) == set(
            json.loads(topics_response)["topics"]
        )
