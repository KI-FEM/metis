import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .data import test_get_topics_data
from .database_mock import DatabaseMock

sys.path.append(str(Path(Path(__file__).parent.parent.parent / "src")))
from bots.study.helpers.helpers import get_llms_for_purpose
from framework.api_types.ai_models import (
    LLMPurpose,
    PurposeConfigModel,
    PurposeListConfigModel,
)
from framework.router import Router


class TestRouter:
    """Test the Router class."""

    @pytest.fixture
    def app(self):
        """Set up the Flask app for the tests."""
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
    def og_passthrough_bot(self, monkeypatch):
        """Get the original passthrough bot for the tests."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        from bots.passthrough.passthrough_bot import (
            passthrough_bot as og_passthrough_bot,
        )

        return og_passthrough_bot

    def mock_db(self, mocker):
        """Mock the database for testing."""
        mocked_db = DatabaseMock()
        """Replace the database with a mock for testing."""
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

    @pytest.fixture
    def passthrough_bot(self, monkeypatch):
        """Set up the passthrough bot for the tests."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        from bots.passthrough.passthrough_bot import PassthroughBot

        return PassthroughBot()

    def test_router_register_bot(self, router, client, og_passthrough_bot):
        """Test the register_bot method of the Router class."""
        router.register_bot(og_passthrough_bot)

        # Check that the bot was registered correctly
        assert len(router.bots) == 1
        assert list(router.bots.keys()) == ["passthrough"]
        assert router.bots["passthrough"] == og_passthrough_bot

        # Check that the route exists
        response = client.get("/topic/passthrough/modules")
        assert response.status_code == 200

    def test_router_register_bot_twice(
        self, router, passthrough_bot, og_passthrough_bot
    ):
        """Test the register_bot method of the Router class."""
        bot1 = og_passthrough_bot
        bot2 = passthrough_bot
        router.register_bot(bot1)
        assert len(router.bots) == 1

        # Check that registering the a second bot with the same base route
        # raises an error
        with pytest.raises(
            ValueError,
            match="Bot passthrough already registered. "
            "Remove it before registering a new bot.",
        ):
            router.register_bot(bot2)

    def test_get_topics(self, router, client, passthrough_bot):
        """Get the topics from the router."""
        assert len(router.bots) == 0
        from bots.citation.citation_bot import CitationBot

        bot_2 = CitationBot()
        router.register_bot(passthrough_bot)
        router.register_bot(bot_2)
        response = client.get("/topics")
        assert response.status_code == 200
        assert response.json() == test_get_topics_data

    def test_health(self, router, client):
        """Test the /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_ready(self, router, client, mocker):
        """Test the /health/ready endpoint."""
        mocker.patch("openai.resources.models.Models.list", return_value=["something"])
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_health_ready_error(self, router, client, mocker):
        """Test the /health/ready endpoint."""
        mocker.patch("openai.resources.models.Models.list", return_value=[])
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.content == b"LLM service not ready: No models found"

    def test_disabled_bot(self, router, client, passthrough_bot, monkeypatch):
        """Test that configuring the bots disabled the bot."""
        monkeypatch.setenv("ADMIN_KEY", "some_key")
        router.register_bot(passthrough_bot)
        response = client.get("/topics")
        assert response.status_code == 200
        assert response.json() == {
            "topics": [
                {
                    "endpoint": "passthrough",
                    "title": {
                        "de": "Freier Chat",
                        "en": "Free Chat",
                    },
                    "short_description": {
                        "de": "Chatte offen mit unserer KI.",
                        "en": "Chat freely with our AI.",
                    },
                    "long_description": {
                        "de": (
                            "Chatte offen mit unserer KI. Du kannst jede Frage stellen,"
                            " die du möchtest."
                        ),
                        "en": "Chat freely with our AI. You can ask any question you like.",
                    },
                    "modules": [],
                    "type": "basic",
                    "features": [
                        "title",
                        "inspirations",
                        "streaming",
                        "summary",
                        "aimodel",
                    ],
                    "priority": 5,
                    "optional": False,
                    "avatar": None,
                    "color": "#ea964d",
                    "enabled": True,
                    "tag": None,
                }
            ]
        }
        response = client.post(
            "/admin/configure",
            json={"key": "some_key", "enabled": {"passthrough": False}},
        )
        assert response.status_code == 200
        response = client.get("/topics")
        assert response.status_code == 200
        assert response.json() == {
            "topics": [
                {
                    "endpoint": "passthrough",
                    "title": {
                        "de": "Freier Chat",
                        "en": "Free Chat",
                    },
                    "short_description": {
                        "de": "Chatte offen mit unserer KI.",
                        "en": "Chat freely with our AI.",
                    },
                    "long_description": {
                        "de": (
                            "Chatte offen mit unserer KI. Du kannst jede Frage stellen,"
                            " die du möchtest."
                        ),
                        "en": "Chat freely with our AI. You can ask any question you like.",
                    },
                    "modules": [],
                    "type": "basic",
                    "features": [
                        "title",
                        "inspirations",
                        "streaming",
                        "summary",
                        "aimodel",
                    ],
                    "priority": 5,
                    "optional": False,
                    "avatar": None,
                    "color": "#ea964d",
                    "enabled": False,
                    "tag": None,
                }
            ]
        }

    def test_get_learning_types(self, router, client):
        """Get the learning types from the router."""
        from .data import router_learning_types_data

        response = client.get("/learning_types")
        assert response.status_code == 200
        assert response.json() == router_learning_types_data

    def test_get_models(self, router, client, mocker):
        """Get the models from the router."""
        # Mock the config
        self.mock_db(mocker)
        mocker.patch(
            "framework.router.get_ai_models",
            return_value=PurposeListConfigModel(
                purposes=[
                    PurposeConfigModel(
                        id="optimal",
                        label={"en": "Optimal", "de": "Optimal"},
                        description={
                            "en": "Optimal model for everyday tasks.",
                            "de": "Optimales Modell für alltägliche Aufgaben.",
                        },
                        icon="fas fa-check-circle",
                        models=[
                            "llama-3.3",
                            "llama-3.1-sauerkrautlm-70b",
                        ],
                    ),
                    PurposeConfigModel(
                        id="reasoning",
                        label={"en": "Analytical", "de": "Analytisch"},
                        description={
                            "en": "Model for deep thinking tasks.",
                            "de": "Modell für tiefes Denken.",
                        },
                        icon="fas fa-brain",
                        models=[
                            "llama-3.1-sauerkrautlm-70b",
                        ],
                    ),
                ]
            ),
        )

        response = client.get("/models")
        assert response.status_code == 200
        assert response.json()["purposes"] == [
            {
                "id": "optimal",
                "label": {"en": "Optimal", "de": "Optimal"},
                "description": {
                    "en": "Optimal model for everyday tasks.",
                    "de": "Optimales Modell für alltägliche Aufgaben.",
                },
                "icon": "fas fa-check-circle",
                "healthy": True,
            },
            {
                "id": "reasoning",
                "label": {"en": "Analytical", "de": "Analytisch"},
                "description": {
                    "en": "Model for deep thinking tasks.",
                    "de": "Modell für tiefes Denken.",
                },
                "icon": "fas fa-brain",
                "healthy": True,
            },
        ]

    @pytest.mark.asyncio
    async def test_select_llm_by_purpose(
        self, router, client, monkeypatch, mocker, tmp_path
    ):
        """Test the purpose-based LLM selection through API calls."""
        # Reset the global cached_purposes before the test
        import bots.study.helpers.helpers as helpers_module

        helpers_module.cached_purposes = None
        self.mock_db(mocker)

        # Test normal purpose - should select llama-3.3
        llms = await get_llms_for_purpose(LLMPurpose.OPTIMAL)
        assert [llm.model_name for llm in llms] == [
            "llama-3.3",
            "llama-3.1-sauerkrautlm-70b",
        ]

        # Test thinking purpose
        assert [
            llm.model_name
            for llm in await get_llms_for_purpose(LLMPurpose.REASONING)
        ] == ["llama-3.1-sauerkrautlm-70b"]

    def test_personality(self, router, client):
        """Test the personality to learning type conversion."""
        response = client.get("/learning_types/from_personality/ISTJ")
        assert response.status_code == 200
        assert response.json() == {"learning_type": "SENSING"}
        response = client.get("/learning_types/from_personality/ENTP")
        assert response.status_code == 200
        assert response.json() == {"learning_type": "INTUITIVE"}
        response = client.get("/learning_types/from_personality/asdf")
        assert response.status_code == 422

    def test_admin_configure_no_key(self, router, client, monkeypatch):
        """Test the admin route with a wrong key."""
        monkeypatch.setenv("ADMIN_KEY", "admin")
        response = client.post(
            "/admin/configure",
            json={
                "key": "wrong_key",
                "enabled": {"study_competence": True, "passthrough": False},
            },
        )
        assert not response.json()["success"]
        assert response.json()["error_message"] == "Invalid key."

    def test_admin_configure(self, router, client, monkeypatch):
        """Test the admin route to disable bots."""
        monkeypatch.setenv("ADMIN_KEY", "admin")
        # Make sure the passthrough bot is registered with the router
        from bots.citation.citation_bot import citation_bot
        from bots.passthrough.passthrough_bot import passthrough_bot

        router.register_bot(passthrough_bot)
        router.register_bot(citation_bot)

        response = client.post(
            "/admin/configure",
            json={
                "key": "admin",
                "enabled": {"citation": True, "passthrough": False},
            },
        )
        assert response.status_code == 200
        assert response.json()["success"]

        bots = client.get("/topics")
        assert bots.status_code == 200
        bot_enabled = [
            bot["enabled"]
            for bot in bots.json()["topics"]
            if bot["endpoint"] == "passthrough"
        ]
        assert len(bot_enabled) == 1
        assert not bot_enabled[0]

    def test_admin_config(self, router, client, monkeypatch, mocker):
        """Test the config admin route."""
        self.mock_db(mocker)
        monkeypatch.setenv("ADMIN_KEY", "admin")
        response = client.get("/admin/config?key=admin")
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "config": {"MODELS_REFRESH_THRESHOLD": 100},
            "purposes": {
                "optimal": {
                    "code": "optimal",
                    "enabled": True,
                    "icon": "fas fa-check-circle",
                    "idpurposes": 1,
                    "models": ["llama-3.3", "llama-3.1-sauerkrautlm-70b"],
                },
                "reasoning": {
                    "code": "reasoning",
                    "enabled": True,
                    "icon": "fas fa-brain",
                    "idpurposes": 2,
                    "models": ["llama-3.1-sauerkrautlm-70b"],
                },
            },
            "error_message": "",
        }
        # test updating config
        mock_save = mocker.patch("framework.config.save_config")
        response = client.post(
            "/admin/config",
            json={
                "key": "admin",
                "updates": {"MODELS_REFRESH_THRESHOLD": 200},
            },
        )
        assert response.status_code == 200
        assert response.json() == {"success": True, "error_message": ""}
        mock_save.assert_called_once_with({"MODELS_REFRESH_THRESHOLD": 200})

    def test_init_chat_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test init_chat endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's init_chat method to raise an exception
        mocker.patch.object(
            passthrough_bot, "init_chat", side_effect=Exception("Test exception")
        )

        response = client.post(
            "/topic/passthrough",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Test exception"
        assert response_data["error"]["context"]["method"] == "init_chat"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_chat_invoke_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test chat_invoke endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's chat_invoke method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "chat_invoke",
            side_effect=Exception("Chat invoke test exception"),
        )

        response = client.post(
            "/topic/passthrough/message",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Chat invoke test exception"
        assert response_data["error"]["context"]["method"] == "chat_invoke"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_update_title_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test update_title endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's update_title method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "update_title",
            side_effect=Exception("Title update test exception"),
        )

        response = client.post(
            "/topic/passthrough/title",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["title"] == ""
        assert response_data["error"]["error"] == "Title update test exception"
        assert response_data["error"]["context"]["method"] == "update_title"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_inspiration_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test inspiration endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's inspirations method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "inspirations",
            side_effect=Exception("Inspiration test exception"),
        )

        response = client.post(
            "/topic/passthrough/inspiration",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Inspiration test exception"
        assert response_data["error"]["context"]["method"] == "inspirations"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_quiz_exception_handling(self, router, client, passthrough_bot, mocker):
        """Test quiz endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's quiz method to raise an exception
        mocker.patch.object(
            passthrough_bot, "quiz", side_effect=Exception("Quiz test exception")
        )

        response = client.post(
            "/topic/passthrough/quiz",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["title"] == ""
        assert response_data["description"] == ""
        assert response_data["questions"] == []
        assert response_data["error"]["error"] == "Quiz test exception"
        assert response_data["error"]["context"]["method"] == "quiz"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_initial_quiz_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test initial_quiz endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's initial_quiz method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "initial_quiz",
            side_effect=Exception("Initial quiz test exception"),
        )

        response = client.post(
            "/topic/passthrough/initial_quiz",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["title"] == ""
        assert response_data["description"] == ""
        assert response_data["questions"] == []
        assert response_data["quiz_questions_asked_per_level"] == [0, 0, 0]
        assert response_data["error"]["error"] == "Initial quiz test exception"
        assert response_data["error"]["context"]["method"] == "initial_quiz"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_answer_initial_quiz_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test answer_initial_quiz endpoint returns proper error response."""
        router.register_bot(passthrough_bot)

        # Mock the bot's answer_initial_quiz method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "answer_initial_quiz",
            side_effect=Exception("Answer initial quiz test exception"),
        )

        response = client.post(
            "/topic/passthrough/answer_initial_quiz",
            json={
                "correct_question_ids": [1, 2, 3],
                "questions_asked_per_level": [2, 2, 2],
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["quiz_performance_below"] == 0
        assert response_data["quiz_performance_at_level"] == 0
        assert response_data["quiz_performance_above"] == 0
        assert response_data["quiz_recommended_change"] == 0
        assert response_data["error"]["error"] == "Answer initial quiz test exception"
        assert response_data["error"]["context"]["method"] == "answer_initial_quiz"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_answer_quiz_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test answer_quiz endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's answer_quiz method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "answer_quiz",
            side_effect=Exception("Answer quiz test exception"),
        )

        response = client.put(
            "/topic/passthrough/quiz",
            json={
                "questions": [],
                "answers": [],
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Answer quiz test exception"
        assert response_data["error"]["context"]["method"] == "answer_quiz"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_feedback_exception_handling(self, router, client, passthrough_bot, mocker):
        """Test feedback endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's feedback method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "feedback",
            side_effect=Exception("Feedback test exception"),
        )

        response = client.post(
            "/topic/passthrough/feedback",
            json={
                "feedback": {"learning_type_rating": 5, "comment": "Great session!"},
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Feedback test exception"
        assert response_data["error"]["context"]["method"] == "feedback"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_plan_session_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test plan_session endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's plan_session method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "plan_session",
            side_effect=Exception("Plan session test exception"),
        )

        response = client.post(
            "/topic/passthrough/plan-session",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["recommended_topics"] == []
        assert response_data["recommended_date"] == ""
        assert response_data["error"]["error"] == "Plan session test exception"
        assert response_data["error"]["context"]["method"] == "plan_session"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_summarize_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test summarize endpoint returns proper error when bot raises exception."""
        router.register_bot(passthrough_bot)

        # Mock the bot's summarize method to raise an exception
        mocker.patch.object(
            passthrough_bot,
            "summarize",
            side_effect=Exception("Summarize test exception"),
        )

        response = client.post(
            "/topic/passthrough/summarize",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["summary"] == ""
        assert response_data["keep_last_messages_until"] == -1
        assert response_data["error"]["error"] == "Summarize test exception"
        assert response_data["error"]["context"]["method"] == "summarize"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_action_callback_exception_handling(
        self, router, client, passthrough_bot, mocker
    ):
        """Test action_callback endpoint returns proper error response."""
        router.register_bot(passthrough_bot)

        # Create a mock async function that raises an exception
        async def mock_action(request):
            raise Exception("Action callback test exception")

        # Add the mock route to the bot's _routes
        passthrough_bot._routes = {"test_action": mock_action}

        response = client.post(
            "/topic/passthrough/test_action",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        assert response_data["error"]["error"] == "Action callback test exception"
        assert response_data["error"]["context"]["method"] == "test_action"
        assert response_data["error"]["context"]["topic"] == "passthrough"

    def test_action_callback_endpoint_not_found(self, router, client, passthrough_bot):
        """Test action_callback endpoint error when endpoint not found."""
        router.register_bot(passthrough_bot)

        # Ensure _routes is empty or doesn't contain the endpoint
        passthrough_bot._routes = {}

        response = client.post(
            "/topic/passthrough/nonexistent_action",
            json={
                "id": "123",
                "response_preferences": {
                    "detail": 1,
                    "illustration": 4,
                    "language_style": 4,
                    "humour": 2,
                    "creativity": 1,
                    "emojis": 3,
                },
                "language": "en",
                "chat_history": [],
                "streaming": False,
            },
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"] == []
        error_msg = "Action nonexistent_action not found in bot passthrough."
        assert response_data["error"]["error"] == error_msg
        assert response_data["error"]["context"]["method"] == "nonexistent_action"
        assert response_data["error"]["context"]["topic"] == "passthrough"
