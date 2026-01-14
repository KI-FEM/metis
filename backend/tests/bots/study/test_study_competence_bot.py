import json
import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.messages import ToolCall

from ..base_bot_test import FAKE_TIME, BaseBotTest, FakeListLLMStructured, FakeVectorDB
from ..data import (
    initial_quiz_answers_data,
    initial_quiz_data,
    localized_title_prompt_output,
    open_conversation_data,
    submit_test_data,
)
from ..database_mock import DatabaseMock
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))

from bots.base_bot import ResponseGenerationData
from bots.study.agents.lead_agent import (
    get_agent_prompt,
    stream_open_conversation_agent,
)
from bots.study.localization import localization
from bots.study.localization.base_local import BaseLocalization
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message, RequestModel, MessageType
from framework.api_types.response_format import Source
from framework.api_types.response_preferences import ResponsePreferences


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
                    assert prop in localization[locale], (
                        f"Missing {prop} in {locale} localization"
                    )

    def test_get_modules(self, client, mocker):
        """Test '/modules' endpoint."""
        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_modules",
            return_value=[
                {
                    "id": 1,
                    "code": "resilience",
                    "title": {"de": "Resilienz", "en": "Resilience"},
                },
                {
                    "id": 2,
                    "code": "self_efficacy",
                    "title": {"de": "Selbstwirksamkeit", "en": "Self-Efficacy"},
                },
            ],
        )
        response = self.get_request("/modules", client)
        assert response.status_code == 200
        assert response.json() == {
            "modules": [
                {
                    "id": 1,
                    "code": "resilience",
                    "title": {"de": "Resilienz", "en": "Resilience"},
                },
                {
                    "id": 2,
                    "code": "self_efficacy",
                    "title": {"de": "Selbstwirksamkeit", "en": "Self-Efficacy"},
                },
            ]
        }

    def test_startchat_greeting(self, client, mocker):
        """Test '/' endpoint when starting a fresh chat."""
        self.mock_db(mocker)

        fake_structured_llm = FakeListLLMStructured(
            responses=["Hello! How can I assist you today?"]
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai",
            return_value=fake_structured_llm,
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm",
            return_value=fake_structured_llm,
        )

        PromptPatcher().add_prompt(
            prompt=[{"content": "bla bla {{user_memory}}", "role": "system"}],
            name="competence-greeting-en",
        ).add_prompt(
            prompt="This is the competence description.",
            name="competence-description-en",
            prompt_type="text",
        ).patch(mocker)

        response = self.post_request(
            "/",
            {
                **self.default_data,
                "storage": {"selected_competence": "resilience"},
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {
                "learner_model": {
                    "competences": {
                        "COMP1": {
                            "competence_code": "COMP1",
                            "competence_id": 1,
                            "competence_level": 1,
                            "completed": False,
                            "concepts": {
                                "Concept_personal_resilience": {
                                    "completed": False,
                                    "concept_code": "Concept_personal_resilience",
                                    "concept_id": 1,
                                    "custom_learning_goals": "",
                                    "learning_units": {
                                        "LU_create_resilience_example": {
                                            "code": "LU_create_resilience_example",
                                            "completed": False,
                                            "id": 1,
                                            "last_quizzed": None,
                                            "last_seen": None,
                                            "name": {
                                                "de": "Erstelle Resilienz Beispiel",
                                                "en": "Create Resilience Example",
                                            },
                                            "times_correct": 0,
                                            "times_quizzed": 0,
                                            "times_seen": 0,
                                        },
                                    },
                                    "name": {
                                        "de": "Persönliche Resilienz",
                                        "en": "Personal Resilience",
                                    },
                                },
                            },
                            "name": {
                                "de": "Kompetenz 1",
                                "en": "Competence 1",
                            },
                        },
                    },
                    "learning_units": {},
                },
            },
            "messages": [
                {
                    "type": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                        "source": "init_chat",
                    },
                    "thoughts": None,
                    "content": ("Hello! How can I assist you today?"),
                    "buttons": [],
                }
            ],
            "error": None,
        }

    # TODO: Fix this test -> chain.ainvoke fails -> returns fallback in study_competence_bot.py
    def test_suggested_questions(self, client, mocker):
        """Test '/inspiration' endpoint."""
        self.mock_db(mocker)

        fake_structured_llm = FakeListLLMStructured(
            responses=[
                '{"questions": ["What is resilience?", "How can I improve my resilience?"]}'
            ]
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai",
            return_value=fake_structured_llm,
        )

        PromptPatcher().add_prompt(
            prompt=[{"content": "Generate inspirations", "role": "system"}],
            name="competence-generate-inspirations-en",
        ).patch(mocker)

        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_vector_store",
            return_value=FakeVectorDB([Document("test content", id="1")]),
        )
        mocker.patch(
            "framework.rag.retrievers.sub_doc_retriever.SubDocRetriever.retrieve",
            return_value=[(Document("test content", id="1"), 1.0)],
        )

        response = self.post_request(
            "/inspiration",
            {
                **self.default_data,
                "storage": {
                    "selected_competence": "resilience",
                    "skill_level": 1,
                    "learner_model": [],
                },
                "chat_history": [
                    {
                        "content": "Hello! I'm interested in learning about resilience.",
                        "type": "user",
                        "buttons": [],
                        "timestamp": "2024-01-01T00:00:00.000Z",
                        "meta_information": {},
                    },
                    {
                        "content": "Great! I can help you learn about resilience.",
                        "type": "assistant",
                        "buttons": [],
                        "timestamp": "2024-01-01T00:00:01.000Z",
                        "meta_information": {"sources": None, "llm_model": None},
                    },
                ],
            },
            client,
        )

        assert response.status_code == 200
        assert response.json() == {
            "error": None,
            "messages": ["What is resilience?", "How can I improve my resilience?"],
            "storage": {},
        }

    def test_get_localized_langfuse_prompt(self, mocker, monkeypatch):
        """Test the get_localized_langfuse_prompt function."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(
                content="Hi How are you?", type=MessageType.ASSISTANT, timestamp="0"
            ),
            Message(
                content="I am good. How about you?",
                type=MessageType.USER,
                timestamp="1",
            ),
        ]
        response_preferences = ResponsePreferences(
            detail=1, illustration=4, language_style=4, humour=2, creativity=1, emojis=3
        )

        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{competence_role}}\n{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\nHi",
                    "role": "system",
                },
                {"content": "Hello {{name}}.", "role": "user"},
            ],
            name="title-en",
        ).add_prompt(
            prompt="This is the competence description.",
            name="competence-description-en",
            prompt_type="text",
        ).patch(mocker)

        from bots.study.study_competence_bot import get_localized_langfuse_prompt

        assert (
            get_localized_langfuse_prompt(
                "title",
                LocaleType.EN,
                response_preferences,
                chat=chat,
                prompt_type="chat",
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

    def test_select_module(self, client, fake_llm, mocker):
        """Test '/select_module' endpoint."""
        self.mock_db(mocker)
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai",
            return_value=FakeListLLMStructured(
                responses=['{"introduction": "This is a fake response."}']
            ),
        )

        PromptPatcher().add_prompt(
            prompt="Some summarization query",
            name="competence-introduction-summarization-en",
            prompt_type="text",
        ).add_prompt(
            prompt=[
                {
                    "content": "Some introduction prompt",
                    "role": "system",
                },
            ],
            name="competence-introduction-en",
            prompt_type="chat",
        ).patch(mocker)

        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_vector_store",
            return_value=FakeVectorDB([Document("bla bla bla", id="1")]),
        )

        def mocked_rerank(query, retrieved_documents):
            return retrieved_documents

        mocker.patch(
            "framework.rag.retrievers.sub_doc_retriever.SubDocRetriever.rerank",
            side_effect=mocked_rerank,
        )

        response = self.post_request(
            "/select_competence",
            {
                **self.default_data,
                "storage": {"selected_competence": "resilience", "skill_level": 1},
            },
            client,
        )
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["messages"]) > 0
        assert response_data["messages"][0]["content"] == "This is a fake response."

    def patch_llm_prompt(self, mocker):
        """Patch the chat prompts for testing."""
        PromptPatcher().add_prompt(
            name="competence-open-conversation-en",
            prompt=[
                {
                    "content": "{{competence_role}}\n{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\n{{topic}}\n{{includes_summary}}\n{{current_level}}\n{{previous_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{context}}",
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

    def patch_agent_prompt(self, mocker):
        """Patch the agent prompts for testing."""
        PromptPatcher().add_prompt(
            name="competence-lead-agent-en",
            prompt=[
                {
                    "content": "{{current_level}}\n{{previous_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{user_memory}}",
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

    @pytest.mark.skip(reason="TODO: Test quiz agent later on")
    def test_take_test(self, client, mocker):
        """Test '/quiz' endpoint."""
        self.mock_db(mocker)
        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_vector_store",
            return_value=FakeVectorDB([Document("bla bla bla", id="1")]),
        )

        quiz = {
            "title": "This is a title",
            "description": "This is a description",
            "questions": [
                {
                    "id": 1,
                    "question": "This is a question",
                    "learning_unit": 69,
                    "type": "single-choice",
                    "options": [
                        {"id": 1, "label": "This is an answer", "correct": True}
                    ],
                }
            ],
            "storage": {},
            "error": None,
        }

        fake_llm = FakeListLLMStructured(
            responses=[
                json.dumps(quiz),
            ]
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=fake_llm
        )

        def mocked_rerank(query, retrieved_documents):
            return retrieved_documents

        mocker.patch(
            "framework.rag.retrievers.sub_doc_retriever.SubDocRetriever.rerank",
            side_effect=mocked_rerank,
        )

        PromptPatcher().add_prompt(
            prompt="Learning Goal {{idlearningunit}}: {{learning_goal}}\nExample Task: {{task}}\nExample Solution: {{solution}}",
            name="competence-learning-unit-format-en",
            prompt_type="text",
        ).add_prompt(
            name="competence-quiz-retrieval-en",
            prompt_type="text",
            prompt="This is the quiz retrieval prompt.",
        ).add_prompt(
            name="competence-quiz-en",
            prompt=[
                {
                    "content": "{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\n{{topic}}\n{{number_of_questions}}\n{{current_level}}\n{{custom_learning_goals}}\n{{goal_level}}\n{{learning_goals}}\n{{context}}",
                    "role": "system",
                },
            ],
        ).patch(mocker)
        response = self.post_request("/quiz", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == quiz

    @pytest.mark.skip(reason="TODO: Test quiz agent later on")
    def test_submit_test(self, client, mocker, monkeypatch):
        """Test PUT '/quiz' endpoint."""
        feedback = {
            "user_feedback": "This is a feedback",
        }

        fake_llm = FakeListLLMStructured(
            responses=[
                json.dumps(feedback),
            ]
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=fake_llm
        )

        PromptPatcher().add_prompt(
            name="competence-quiz-conclusion-en",
            prompt=[
                {
                    "content": "{{preferences_lod}}\n{{preferences_ill}}\n{{preferences_las}}\n{{preferences_hum}}\n{{preferences_cre}}\n{{preferences_emo}}\n{{questions}}\n{{answers}}\n",
                    "role": "system",
                },
            ],
        ).patch(mocker)

        mocker.patch(
            "bots.study.quiz.get_timestamp", return_value=FAKE_TIME.isoformat()
        )

        response = self.put_request("/quiz", submit_test_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "instructions": [],
            "storage": {
                "learner_model": [
                    {
                        "code": "bla",
                        "id": 69,
                        "times_seen": 0,
                        "last_seen": None,
                        "name": {
                            "de": "Neue Lerneinheit",
                            "en": "New Learning Unit",
                        },
                        "times_quizzed": 1,
                        "times_correct": 0,
                        "last_quizzed": "2024-12-25T17:05:55",
                        "completed": False,
                    }
                ]
            },
            "messages": [
                {
                    "type": "user",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "content": "Submitted a quiz.",
                    "thoughts": None,
                    "buttons": [],
                },
                {
                    "type": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": "llama-4",
                    },
                    "content": "This is a feedback",
                    "thoughts": None,
                    "buttons": [],
                },
            ],
            "error": None,
            "error": None,
        }

    def test_take_initial_quiz(self, client, mocker):
        """Test '/initial_quiz' endpoint."""
        self.mock_db(mocker)
        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_vector_store",
            return_value=FakeVectorDB([Document("bla bla bla", id="1")]),
        )

        # Because the initial quiz randomized the options, only one option is used in this test, so that the test remains deterministic
        initial_quiz = {
            "id": "initial_quiz_1",
            "title": "Initial Assessment Quiz",
            "description": "This quiz assesses your current knowledge level",
            "questions": [
                {
                    "type": "multiple-choice",
                    "options": ["Option A"],
                    "solution": [0],
                    "feedback": None,
                    "is_correct": None,
                    "id": 1,
                    "title": "Question 1",
                    "text": "This is an initial quiz question",
                    "hint": "Choose the correct options.",
                    "learning_unit": "LU_initial",
                    "score": [0, 1],
                    "answer": None,
                    "answered": False,
                }
            ],
            "score": [0, 0],
            "quiz_questions_asked_per_level": [2, 2, 2],
            "completed": False,
            "error": None,
        }

        fake_llm = FakeListLLMStructured(
            responses=[
                json.dumps(initial_quiz),
            ]
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai", return_value=fake_llm
        )

        def mocked_rerank(query, retrieved_documents):
            return retrieved_documents

        mocker.patch(
            "framework.rag.retrievers.sub_doc_retriever.SubDocRetriever.rerank",
            side_effect=mocked_rerank,
        )

        # TODO: check why or if prompts are "used up" -> initial quiz uses competence-learning-unit-format-en 3 times
        PromptPatcher().add_prompt(
            prompt="Learning Goal {{idlearningunit}}: {{learning_goal}}\nExample Task: {{task}}\nExample Solution: {{solution}}",
            name="competence-learning-unit-format-en",
            prompt_type="text",
        ).add_prompt(
            prompt="Learning Goal {{idlearningunit}}: {{learning_goal}}\nExample Task: {{task}}\nExample Solution: {{solution}}",
            name="competence-learning-unit-format-en",
            prompt_type="text",
        ).add_prompt(
            prompt="Learning Goal {{idlearningunit}}: {{learning_goal}}\nExample Task: {{task}}\nExample Solution: {{solution}}",
            name="competence-learning-unit-format-en",
            prompt_type="text",
        ).add_prompt(
            name="competence-quiz-retrieval-en",
            prompt_type="text",
            prompt="This is the initial quiz retrieval prompt.",
        ).add_prompt(
            name="competence-initial-quiz-en",
            prompt=[
                {
                    "content": "{{context}}\n{{number_of_questions}}\n{{current_level}}\n{{learning_goals_at_level}}\n{{learning_goals_below_level}}\n{{learning_goals_above_level}}\n{{custom_learning_goals}}",
                    "role": "system",
                },
            ],
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text",
        ).patch(mocker)

        response = self.post_request("/initial_quiz", initial_quiz_data, client)
        assert response.status_code == 200
        assert response.json() == initial_quiz

    def test_submit_initial_quiz(self, client, mocker):
        """Test '/answer_initial_quiz' endpoint."""
        self.mock_db(mocker)

        expected_response = {
            "quiz_performance_below": 2,
            "quiz_performance_at_level": 0,
            "quiz_performance_above": 0,
            "quiz_recommended_change": 0,
            "error": None,
        }

        response = self.post_request(
            "/answer_initial_quiz", initial_quiz_answers_data, client
        )
        assert response.status_code == 200
        assert response.json() == expected_response

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
                    "type": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "content": (
                        "Thank you for your feedback! I am sorry to hear that you are not "
                        "satisfied. Try to change your learning type in the personalisation "
                        "settings and test it out 🙏 "
                    ),
                    "buttons": [],
                },
            ],
            "error": None,
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
                    "type": "assistant",
                    "meta_information": {
                        "sources": None,
                        "citations": None,
                        "llm_model": None,
                    },
                    "thoughts": None,
                    "content": (
                        "Thank you for your feedback! I am glad to hear that you are satisfied "
                        "with my assistance. 😊 "
                    ),
                    "buttons": [],
                },
            ],
            "error": None,
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
                **self.default_data,
                "feedback": {"comment": "I like the bot", "learning_type_fit": "asdf"},
            },
            client,
        )
        assert response.status_code == 422

    @pytest.mark.skip(reason="Cannot test agent at the moment")  # TODO: Fix this test
    def test_open_conversation(self, client, fake_llm, mocker):
        """Test '/message' endpoint."""
        self.mock_db(mocker)
        self.mock_db(mocker)
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai",
            return_value=FakeListLLMStructured(
                responses=["This is some answer for the agent to stop its processing."]
            ),
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm",
            return_value=FakeListLLMStructured(
                responses=["Resilience\nLearning\nResilienz\nLernen"]
            ),
        )
        mocker.patch(
            "langchain.retrievers.multi_query.MultiQueryRetriever.ainvoke",
            return_value=[Document("bla bla bla", id="1", metadata={"idchunk": 1})],
        )

        mocker.patch(
            "bots.study.study_competence_bot.StudyCompetenceBot.get_vector_store",
            return_value=FakeVectorDB(
                [Document("bla bla bla", id="1", metadata={"idchunk": 1})]
            ),
        )

        self.patch_agent_prompt(mocker)
        response = self.post_request("/message", open_conversation_data, client)
        assert response.status_code == 200
        response_data = response.json()
        assert (
            response_data["messages"][0]["content"]
            == "This is a fake response [source_id: 1]."
        )

    def test_send_message_streaming(self, client, mocker, fake_llm):
        """Test streaming responses in open_conversation_base."""
        # Mock the LLM to return a predetermined response
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)

        # Mock the prompts
        self.patch_llm_prompt(mocker)

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
                    title="Test Source", chunk="Test content", url="https://test.com"
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
        assert first_chunk_data["choices"][0]["delta"]["type"] == "assistant"
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
        self.mock_db(mocker)
        self.mock_db(mocker)

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

        # Create a request with necessary data
        request_data = {
            "storage": {"selected_competence": "resilience", "skill_level": "beginner"}
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
        assert len(response_data["recommended_topics"]) == 2

        # Check that the recommended date is a valid ISO format date
        import datetime

        try:
            datetime.date.fromisoformat(response_data["recommended_date"])
            date_valid = True
        except ValueError:
            date_valid = False
        assert date_valid, "Recommended date is not in valid ISO format"

        # Verify the recommended topics match what we expected
        assert response_data["recommended_topics"] == ["Concept 1", "Concept 2"]

    # AGENT FUNCTIONS

    def fake_request(self):
        """Create a fake request for testing agent functions."""
        return RequestModel(
            id="123",
            language="en",
            chat_history=[
                Message(
                    type=MessageType.USER,
                    content="Hello",
                    timestamp="2025-01-01T00:00:00.000Z",
                ),
                Message(
                    type=MessageType.ASSISTANT,
                    content="Hi there! How can I help you?",
                    timestamp="2025-01-01T00:01:00.000Z",
                ),
            ],
            storage={"chat_id": "test-chat-id"},
            llm=None,
            streaming=False,
            response_preferences=ResponsePreferences(
                detail=2,
                illustration=1,
                language_style=2,
                humour=1,
                creativity=3,
                emojis=1,
            ),
        )

    @pytest.mark.asyncio
    async def test_get_agent_prompt(self, mocker):
        """Test the agent's get prompt funciton."""
        from langchain_core.messages import SystemMessage

        self.mock_db(mocker)

        PromptPatcher().add_prompt(
            name="competence-lead-agent-en",
            prompt=[
                {
                    "content": "{{learner_model}}\n{{user_memory}}",
                    "role": "system",
                },
            ],
        ).patch(mocker)

        sys_message, config = await get_agent_prompt(self.fake_request())
        assert sys_message is not None
        assert isinstance(sys_message, SystemMessage)

    @pytest.mark.asyncio
    async def test_stream_agent(self, mocker, client, monkeypatch):
        """Test the agent's streaming functionality."""
        self.mock_db(mocker)
        _ = client

        async def mock_stream_chunks(*args, **kwargs):
            chunks = [
                'data: {"choices": [{"delta": {"content": "First chunk"}}]}\n\n',
                'data: {"choices": [{"delta": {"content": "Second chunk"}}]}\n\n',
                'data: {"choices": [{"delta": {"content": "Third chunk"}}]}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        mocker.patch(
            "bots.study.agents.lead_agent.stream_agent_and_queue",
            side_effect=mock_stream_chunks,
        )
        from langchain_core.callbacks import (
            BaseCallbackHandler,
        )

        mocker.patch(
            "framework.chains.base_chain.BaseChain.get_langfuse_callback",
            return_value=BaseCallbackHandler(),
        )
        PromptPatcher().add_prompt(
            name="competence-lead-agent-en",
            prompt=[
                {
                    "content": "{{learner_model}}\n{{user_memory}}",
                    "role": "system",
                },
            ],
        ).patch(mocker)

        chunks = []
        async for chunk in stream_open_conversation_agent(
            self.fake_request(), DatabaseMock(), None
        ):
            print(chunk)
            assert "data: " in chunk
            assert (
                len(chunk) > 10
            )  # Arbitrary length check to ensure content is present
            chunks.append(chunk)

        assert len(chunks) > 2  # Ensure multiple chunks were received

    # TOOL TESTS

    @pytest.mark.asyncio
    async def test_think_tool(self, mocker):
        """Test the think tool."""
        import asyncio

        from bots.study.agents.tools import think

        queue = asyncio.Queue()
        config = {
            "configurable": {
                "queue": queue,
                "request": self.fake_request(),
                "thread_id": "123",
            }
        }

        result = await think.ainvoke(
            input={
                "thought": "I need to analyze the user's question carefully",
                "thought_summary": "Analyzing question",
            },
            config=config,
        )

        assert (
            result
            == "The following thought was saved: I need to analyze the user's question carefully"
        )
        # Check that an event was put in the queue
        chunk = await queue.get()
        assert "info:" in chunk
        assert "think" in chunk

    @pytest.mark.asyncio
    async def test_retrieve_additional_information_tool(self, mocker):
        """Test the retrieve_additional_information tool."""
        import asyncio

        from bots.study.agents.tools import retrieve_additional_information

        queue = asyncio.Queue()

        # Mock database
        mock_db = DatabaseMock()
        mocker.patch.object(
            mock_db,
            "get_language",
            return_value=type("Language", (), {"idlanguage": 1})(),
        )

        # Mock retriever
        mock_retriever = mocker.Mock()
        retrieved_docs = [
            (Document("Document 1 content", id="1"), 0.9),
            (Document("Document 2 content", id="2"), 0.8),
        ]
        mock_retriever.retrieve = mocker.AsyncMock(return_value=retrieved_docs)
        mock_retriever.rerank = mocker.AsyncMock(
            return_value=[doc for doc, _ in retrieved_docs]
        )

        config = {
            "configurable": {
                "queue": queue,
                "locale": LocaleType.EN,
                "db": mock_db,
                "retriever": mock_retriever,
                "competence_id": 1,
                "request": self.fake_request(),
                "thread_id": "123",
            }
        }

        state = {"context": [], "messages": []}
        result = await retrieve_additional_information.ainvoke(
            input=ToolCall(
                name="retrieve_additional_information",
                args={
                    "query": "What is resilience?",
                    "state": state,
                },
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        # Check that retrieval was called
        mock_retriever.retrieve.assert_called_once()
        mock_retriever.rerank.assert_called_once()

        # Check the result is a Command with updated context
        assert result.update is not None
        assert "context" in result.update
        assert len(result.update["context"]) == 2
        assert "messages" in result.update

    @pytest.mark.asyncio
    async def test_update_conversation_strategy_agent(self, mocker):
        """Test the update_conversation_strategy agent."""
        import asyncio

        from bots.study.agents.strategy_agent import update_conversation_strategy

        mock_strategy_response = {
            "messages": [
                type(
                    "MockMessage",
                    (),
                    {
                        "content": "Updated strategy: Focus on building foundational concepts before advancing to complex topics."
                    },
                )()
            ]
        }

        mocker.patch(
            "bots.study.agents.strategy_agent.start_strategy_agent",
            return_value=mock_strategy_response,
        )

        queue = asyncio.Queue()
        request = RequestModel(
            **{
                **self.default_data,
                "storage": {"conversation_strategy": "Previous strategy"},
                "chat_history": [],
            }
        )

        config = {
            "configurable": {
                "queue": queue,
                "request": request,
                "thread_id": "123",
            }
        }

        state = {
            "tools": ["update_conversation_strategy", "other_tool"],
            "messages": [],
        }

        response_reasoning = "The response was very detailed and on topic."
        addressed_learning_units = ["1", "2"]

        result = await update_conversation_strategy.ainvoke(
            input=ToolCall(
                name="update_conversation_strategy",
                args={
                    "response_reasoning": response_reasoning,
                    "addressed_learning_units": addressed_learning_units,
                    "state": state,
                },
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        # Check that the tool was removed from the tools list
        assert result.update is not None
        assert "tools" in result.update
        assert "update_conversation_strategy" not in result.update["tools"]
        assert "other_tool" in result.update["tools"]

        # Check that a message was added
        assert "messages" in result.update
        assert len(result.update["messages"]) == 1
        assert "Updated strategy" in result.update["messages"][0].content

        # Check that an event was put in the queue
        info_chunk = await queue.get()
        strategy_chunk = await queue.get()

        assert "info:" in info_chunk
        assert "update_conversation_strategy" in info_chunk
        assert "updated_conversation_strategy:" in strategy_chunk
        assert "Focus on building foundational concepts" in strategy_chunk

    @pytest.mark.asyncio
    async def test_formulate_answer_tool(self, mocker):
        """Test the formulate_answer tool."""
        import asyncio

        from bots.study.agents.tools import formulate_answer

        self.mock_db(mocker)

        queue = asyncio.Queue()

        # Mock the LLM
        fake_llm = FakeListLLMStructured(
            responses=['{"answer": "This is the answer", "citations": [0, 1]}']
        )
        mocker.patch(
            "framework.llm.lite_llm.LiteLLM.llm_chatopenai",
            return_value=fake_llm,
        )

        # Mock the prompt
        PromptPatcher().add_prompt(
            name="competence-tool-formulate-answer-en",
            prompt=[
                {
                    "content": "{{task}}\n{{context}}",
                    "role": "system",
                },
            ],
        ).patch(mocker)

        request = RequestModel(
            **{
                **self.default_data,
                "storage": {},
                "chat_history": [],
            }
        )

        config = {
            "configurable": {
                "queue": queue,
                "request": request,
                "locale": LocaleType.EN,
                "learner_model": {},
                "user_memory": "",
                "conversation_strategy": "",
                "thread_id": "123",
            }
        }

        state = {
            "context": [
                Document("Document 1", id="1"),
                Document("Document 2", id="2"),
            ],
            "messages": [],
        }

        result = await formulate_answer.ainvoke(
            input=ToolCall(
                name="formulate_answer",
                args={"task": "Explain resilience", "state": state},
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        assert "Successfully composed and sent response" in result.content

        # Check that messages were added to the queue
        messages = []
        while not queue.empty():
            messages.append(await queue.get())

        assert len(messages) > 0

    @pytest.mark.asyncio
    async def test_update_memory_about_user_tool(self, mocker):
        """Test the update_memory_about_user tool."""
        import asyncio

        from bots.study.agents.tools import update_memory_about_user

        queue = asyncio.Queue()
        config = {
            "configurable": {
                "queue": queue,
                "thread_id": "123",
                "request": self.fake_request(),
            }
        }

        state = {"tools": ["update_memory_about_user", "other_tool"], "messages": []}

        memory = "User is interested in resilience and has a background in psychology"

        result = await update_memory_about_user.ainvoke(
            input=ToolCall(
                name="update_memory_about_user",
                args={"memory": memory, "state": state},
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        # Check that the tool was removed from the tools list
        assert result.update is not None
        assert "tools" in result.update
        assert "update_memory_about_user" not in result.update["tools"]
        assert "other_tool" in result.update["tools"]

        # Check that a message was added
        assert "messages" in result.update
        assert len(result.update["messages"]) == 1

        # Check that an event was put in the queue
        chunk = await queue.get()
        assert "update_memory:" in chunk

    @pytest.mark.asyncio
    async def test_update_learner_model_tool(self, mocker):
        """Test the update_learner_model tool."""
        import asyncio

        from bots.study.agents.tools import update_learner_model
        from framework.api_types.request_format import LearnerModel

        queue = asyncio.Queue()

        learner_model = LearnerModel(
            competences={
                "competence_1": {
                    "competence_id": 1,
                    "competence_code": "competence_1",
                    "completed": False,
                    "competence_level": 1,
                    "name": {
                        "en": "Resilience",
                        "de": "Resilienz",
                    },
                    "concepts": {
                        "concept_1": {
                            "concept_id": 1,
                            "concept_code": "concept_1",
                            "completed": False,
                            "custom_learning_goals": "",
                            "name": {
                                "en": "Concept 1",
                                "de": "Konzept 1",
                            },
                            "learning_units": {
                                "LU_create_resilience_example": {
                                    "id": 69,
                                    "code": "LU_create_resilience_example",
                                    "name": {
                                        "en": "Create Resilience Example",
                                        "de": "Erstelle Resilienz Beispiel",
                                    },
                                    "times_seen": 5,
                                    "last_seen": None,
                                    "times_quizzed": 0,
                                    "times_correct": 0,
                                    "last_quizzed": None,
                                    "completed": False,
                                }
                            },
                        }
                    },
                }
            }
        ).model_dump()

        request = RequestModel(
            **{
                **self.default_data,
                "storage": {"learner_model": learner_model},
                "chat_history": [],
            }
        )

        config = {
            "configurable": {
                "queue": queue,
                "request": request,
                "thread_id": "123",
            }
        }

        state = {"tools": ["update_learner_model", "other_tool"], "messages": []}

        result = await update_learner_model.ainvoke(
            input=ToolCall(
                name="update_learner_model",
                args={
                    "seen_learning_units": ["LU_create_resilience_example"],
                    "state": state,
                },
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        # Check that the tool was removed from the tools list
        assert result.update is not None
        assert "tools" in result.update
        assert "update_learner_model" not in result.update["tools"]
        assert "other_tool" in result.update["tools"]

        # Check that a message was added
        assert "messages" in result.update
        assert len(result.update["messages"]) == 1

        # Check that an event was put in the queue
        chunk = await queue.get()
        assert "update_learner_model:" in chunk

    @pytest.mark.asyncio
    async def test_format_learner_model(self):
        """Test the format_learner_model helper function."""
        from bots.study.agents.tools import format_learner_model
        from framework.api_types.request_format import LearnerModel

        learner_model = LearnerModel(
            competences={
                "competence_1": {
                    "competence_id": 1,
                    "competence_code": "competence_1",
                    "completed": False,
                    "competence_level": 1,
                    "name": {
                        "en": "Resilience",
                        "de": "Resilienz",
                    },
                    "concepts": {
                        "concept_1": {
                            "concept_id": 1,
                            "concept_code": "concept_1",
                            "completed": False,
                            "custom_learning_goals": "",
                            "name": {
                                "en": "Concept 1",
                                "de": "Konzept 1",
                            },
                            "learning_units": {
                                "LU_create_resilience_example": {
                                    "id": 69,
                                    "code": "LU_create_resilience_example",
                                    "name": {
                                        "en": "Create Resilience Example",
                                        "de": "Erstelle Resilienz Beispiel",
                                    },
                                    "times_seen": 5,
                                    "last_seen": None,
                                    "times_quizzed": 0,
                                    "times_correct": 0,
                                    "last_quizzed": None,
                                    "completed": False,
                                }
                            },
                        }
                    },
                }
            }
        ).model_dump()

        result = format_learner_model(learner_model)

        assert "Concept `concept_1`" in result
        assert "Competence Level: 1" in result
        assert "Learning Unit LU_create_resilience_example" in result
        assert "Times Seen: 5" in result
        assert "Completed: No" in result

    @pytest.mark.asyncio
    async def test_create_chunk(self):
        """Test the create_chunk helper function."""
        from bots.study.agents.tools import create_chunk
        from framework.api_types.request_format import MessageType

        request = RequestModel(
            **{
                **self.default_data,
                "storage": {"chat_id": "test_chat_123"},
                "chat_history": [],
            }
        )

        chunk = create_chunk(
            request=request,
            message="Test message",
            llm_model="llama-4",
            message_type=MessageType.ASSISTANT,
        )

        assert "data: " in chunk
        assert "Test message" in chunk
        assert "llama-4" in chunk
        assert "assistant" in chunk

    @pytest.mark.asyncio
    async def test_retrieve_additional_information_rerank_failure(self, mocker):
        """Test retrieve_additional_information when reranking fails."""
        import asyncio

        from bots.study.agents.tools import retrieve_additional_information

        queue = asyncio.Queue()

        # Mock database
        mock_db = DatabaseMock()
        mocker.patch.object(
            mock_db,
            "get_language",
            return_value=type("Language", (), {"idlanguage": 1})(),
        )

        # Mock retriever with failing rerank
        mock_retriever = mocker.Mock()
        retrieved_docs = [
            (Document("Document 1 content", id="1"), 0.9),
        ]
        mock_retriever.retrieve = mocker.AsyncMock(return_value=retrieved_docs)
        mock_retriever.rerank = mocker.AsyncMock(side_effect=Exception("Rerank failed"))

        config = {
            "configurable": {
                "queue": queue,
                "locale": LocaleType.EN,
                "db": mock_db,
                "retriever": mock_retriever,
                "competence_id": 1,
                "thread_id": "123",
                "request": self.fake_request(),
            }
        }

        state = {"context": [], "messages": []}

        result = await retrieve_additional_information.ainvoke(
            input=ToolCall(
                name="retrieve_additional_information",
                args={"query": "What is resilience?", "state": state},
                id="test_id",
                type="tool_call",
            ),
            config=config,
        )

        # Should still return documents even if reranking fails
        assert result.update is not None
        assert "context" in result.update
        assert len(result.update["context"]) == 1

    @pytest.mark.asyncio
    async def test_get_strategy_agent_prompt(self, mocker):
        """Test the get_strategy_agent_prompt function."""
        from bots.study.agents.strategy_agent import get_strategy_agent_prompt

        PromptPatcher().add_prompt(
            name="competence-strategy-agent-en",
            prompt=[
                {
                    "content": "{{learner_model}}\n{{response_reasoning}}\n{{addressed_learning_units}}\n{{user_memory}}\n{{conversation_strategy}}",
                    "role": "system",
                },
            ],
        ).patch(mocker)

        request = RequestModel(
            **{
                **self.default_data,
                "storage": {
                    "learner_model": {"concept_1": {"competence_level": 1}},
                    "user_memory": "User likes practical examples",
                    "conversation_strategy": "Focus on foundational concepts",
                },
                "chat_history": [],
            }
        )

        response_reasoning = "Testing strategy update"
        addressed_learning_units = [1, 2, 3]

        result = await get_strategy_agent_prompt(
            request, response_reasoning, addressed_learning_units
        )

        assert result is not None
        assert "Testing strategy update" in result.content
        assert "1, 2, 3" in result.content
        assert "User likes practical examples" in result.content
