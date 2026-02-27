import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .data import test_get_topics_data

sys.path.append(str(Path(Path(__file__).parent.parent.parent / "src")))
from framework.api_types.ai_models import PurposeConfigModel, PurposeListConfigModel
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
        mocker.patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Mocked timeout"))
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.content == b"Service not ready: Mocked timeout"

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
                    "features": ["title", "inspirations", "streaming", "summary", "aimodel"],
                    "priority": 0,
                    "color": "#ea964d",
                    "enabled": True,
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
                    "features": ["title", "inspirations", "streaming", "summary", "aimodel"],
                    "priority": 0,
                    "color": "#ea964d",
                    "enabled": False,
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
        import os

        lite_llm_url = os.getenv("LITELLM_URL")
        # This method will be used by the mock to replace requests.get
        def mocked_requests_get(*args, **kwargs):
            class MockResponse:
                def __init__(self, json_data, status_code):
                    self.json_data = json_data
                    self.status_code = status_code

                def json(self):
                    return self.json_data

            if args[0] == f"{lite_llm_url}/model/info":
                return MockResponse(
                    {
                        "data": [
                            {
                                "model_name": "llama-3.3",
                                "litellm_params": {
                                    "api_base": "https://chat-ai.academiccloud.de/v1",
                                    "use_in_pass_through": False,
                                    "merge_reasoning_content_in_choices": False,
                                    "model": "openai/llama-3.3-70b-instruct",
                                },
                                "model_info": {"id": "749878973198041793"},
                            },
                            {
                                "model_name": "deepseek-r1",
                                "litellm_params": {
                                    "api_base": "https://llm.scads.ai/v1",
                                    "use_in_pass_through": False,
                                    "merge_reasoning_content_in_choices": False,
                                    "model": "openai/meta-llama/deepseek-r1",
                                },
                                "model_info": {"id": "1239873895734"},
                            },
                        ]
                    },
                    200,
                )
            elif args[0] == f"{lite_llm_url}/health":
                return MockResponse(
                    {
                        "healthy_endpoints": [
                            {
                                "api_base": "https://chat-ai.academiccloud.de/v1",
                                "use_in_pass_through": False,
                                "merge_reasoning_content_in_choices": False,
                                "model": "openai/llama-3.3-70b-instruct",
                                "cache": {"no-cache": True},
                            }
                        ],
                        "unhealthy_endpoints": [
                            {
                                "api_base": "https://llm.scads.ai/v1",
                                "use_in_pass_through": False,
                                "merge_reasoning_content_in_choices": False,
                                "model": "openai/meta-llama/deepseek-r1",
                                "cache": {"no-cache": True},
                            }
                        ],
                    },
                    200,
                )

            return MockResponse(None, 404)

        mocker.patch("requests.get", mocked_requests_get)
        # Mock the config
        mocker.patch("framework.router.get_ai_models", return_value=PurposeListConfigModel(
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
                            "unavailable",
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
            ))

        models_file = Path(__file__).parent.parent.parent / "models.json"
        content_before = False
        if models_file.exists():
            content_before = True
            models_file.rename(models_file.with_suffix(".bak"))
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
                "healthy": False,
            },
        ]
        if content_before:
            models_file.unlink()
            models_file.with_suffix(".bak").rename(models_file)

    def test_select_llm_by_purpose(self, router, client, monkeypatch, mocker, tmp_path):
        """Test the purpose-based LLM selection through API calls."""
        # Create a temporary mock models.json file
        models_json = {
            "models": [
                {
                    "id": "2d036a06cef042d9abc2836ec338c4af74cddbe6d3fb8501ca1be04f1867e75f",
                    "model_name": "openai/llama-3.1-sauerkrautlm-70b-instruct",
                    "label": "llama-3.1-sauerkrautlm-70b",
                    "api_base_url": "https://chat-ai.academiccloud.de/v1",
                    "status": "healthy",
                },
                {
                    "id": "d2386747b229d6c61e8911f4b16e2ae02814b1af542fcdb2b5854f3287b17774",
                    "model_name": "openai/llama-3.3-70b-instruct",
                    "label": "llama-3.3",
                    "api_base_url": "https://chat-ai.academiccloud.de/v1",
                    "status": "healthy",
                },
                {
                    "id": "4ab6fee161b4a339fb9a90bd8652e7c96db282089d06d9bb0c405cfae1252c1d",
                    "model_name": "openai/unavailable",
                    "label": "unavailable",
                    "api_base_url": "https://chat-ai.academiccloud.de/v1",
                    "status": "unhealthy",
                },
            ],
            "timestamp": 1734685954,
        }

        # Mock config.get_config to return test priorities
        def mock_get_config():
            return {
                "AI_MODELS": {
                    "purposes": [
                        {
                            "id": "optimal",
                            "label": {"en": "Optimal", "de": "Optimal"},
                            "description": {
                                "en": "Optimal model for everyday tasks.",
                                "de": "Optimales Modell für alltägliche Aufgaben.",
                            },
                            "icon": "fas fa-check-circle",
                            "models": [
                                "unavailable",
                                "llama-3.3",
                                "llama-3.1-sauerkrautlm-70b",
                            ],
                        },
                        {
                            "id": "reasoning",
                            "label": {"en": "Analytical", "de": "Analytisch"},
                            "description": {
                                "en": "Model for deep thinking tasks.",
                                "de": "Modell für tiefes Denken.",
                            },
                            "icon": "fas fa-brain",
                            "models": [
                                "llama-3.1-sauerkrautlm-70b",
                            ],
                        },
                    ]
                },
                "MAX_MESSAGES_BEFORE_SUMMARIZATION": 64,
                "KEEP_LAST_MESSAGES_UNTIL": 16,
                "MULTI_QUERY_RETRIEVER": False,
                "MODELS_REFRESH_THRESHOLD": 86400,
            }

        # Set up the test environment
        models_file = Path(__file__).parent.parent.parent / "models.json"
        content_before = None
        if models_file.exists():
            content_before = models_file.read_text()

        with Path.open(models_file, "w") as f:
            json.dump(models_json, f)

        # Mock the config
        mocker.patch("framework.config.get_config", mock_get_config)

        # Create a fake LLM that will return a fixed response but capture the model used
        selected_model_id = None

        async def fake_init_chat(self, request):
            nonlocal selected_model_id
            if request.llm:
                selected_model_id = request.llm.label
            from framework.api_types.response_format import Response

            return Response.from_message("Test response")

        # Mock the init_chat method to capture the model ID
        mocker.patch(
            "bots.passthrough.passthrough_bot.PassthroughBot.init_chat", fake_init_chat
        )

        # Make sure the passthrough bot is registered with the router
        from bots.passthrough.passthrough_bot import passthrough_bot

        if "passthrough" not in router.bots:
            router.register_bot(passthrough_bot)

        # Test normal purpose - should select llama-3.3
        response = client.post(
            "/topic/passthrough",
            json={
                "learning_type_id": "INTUITIVE",
                "language": "en",
                "chat_history": [],
                "llm_purpose": "optimal",
                "streaming": False,
            },
        )
        assert response.status_code == 200
        assert selected_model_id == "llama-3.3"

        # Reset for next test
        selected_model_id = None

        # Test thinking purpose
        response = client.post(
            "/topic/passthrough",
            json={
                "learning_type_id": "INTUITIVE",
                "language": "en",
                "chat_history": [],
                "llm_purpose": "reasoning",
                "streaming": False,
            },
        )
        assert response.status_code == 200
        assert selected_model_id == "llama-3.1-sauerkrautlm-70b"

        # Reset for next test
        selected_model_id = None

        # Test edge case - non-existent purpose (should use first available)
        response = client.post(
            "/topic/passthrough",
            json={
                "learning_type_id": "INTUITIVE",
                "language": "en",
                "chat_history": [],
                "llm_purpose": "german",
                "streaming": False,
            },
        )
        assert response.status_code == 200
        # Should select first available model
        assert selected_model_id == "llama-3.1-sauerkrautlm-70b"

        # Restore original models.json if it existed
        if content_before:
            models_file.write_text(content_before)

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
