import asyncio
import inspect
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict

import httpx
import requests
from fastapi import FastAPI, status
from fastapi import Response as FastAPIResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features
from framework import config
from framework.api_types.admin import (
    AdminRequest,
    ConfigReadResponse,
    ConfigUpdateRequest,
    ConfigureTopicsRequest,
    ConfigureTopicsResponse,
)
from framework.api_types.ai_models import (
    LLM,
    AIModelsResponse,
    CachedAIModels,
    CachedPurposes,
    ChatConfig,
    LLMPurpose,
    LLMStatus,
    PurposeConfigModel,
    PurposeListConfigModel,
    PurposeModel,
)
from framework.api_types.learning_type import (
    AvailableLearningTypes,
    LearningTypes,
    LearningTypesResponseModel,
    PersonalityType,
    PersonalityTypeConversionResponse,
)
from framework.api_types.module import ModulesResponse
from framework.api_types.request_format import RequestModel
from framework.api_types.response_format import Response, SummaryResponse, TitleResponse
from framework.api_types.topics import Topic, TopicListModel, TopicType
from framework.config import (
    AI_MODELS,
    MAX_MESSAGES_BEFORE_SUMMARIZATION,
    MODELS_REFRESH_THRESHOLD,
)

logger = logging.getLogger()


class Router:
    """Router for handling requests to the API."""

    def __init__(self, app: FastAPI) -> None:
        """Initialize the router."""
        self.app: FastAPI = app
        self.bots: dict[Topic, BaseBot] = {}
        self.cached_llm_status: Dict[str, str] = {}
        # cache in memory and on disk as fallback
        self.cached_purposes: CachedPurposes = None
        self.cached_ai_models: CachedAIModels = None

        @self.app.get("/learning_types")
        def get_learning_types() -> LearningTypesResponseModel:
            """Retrieve set learning types."""
            response: LearningTypesResponseModel = {"learning_types": []}
            for lt in LearningTypes:
                lt_obj = {
                    "id": lt.value.id.value,
                    "title": lt.value.title,
                    "short_description": lt.value.short_description,
                    "long_description": lt.value.long_description,
                }
                response["learning_types"].append(lt_obj)
            return response

        class StatusModel(BaseModel):
            """Status model."""

            status: str

        # Add health check endpoints
        @self.app.get("/health")
        async def health() -> StatusModel:
            """Liveness probe endpoint - checks if the application is running."""
            return StatusModel(status="ok")

        @self.app.get("/health/ready")
        async def health_ready():
            """Readiness probe endpoint.

            You might want to add more checks here, such as:
            - Database connectivity
            - External service dependencies
            - Cache availability
            """
            try:
                base_url = os.getenv("LITELLM_URL")
                if not base_url:
                    logger.error("Health check failed: LITELLM_URL not set.")
                    return FastAPIResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content="LLM service not ready: LITELLM_URL not set.",
                    )
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url}/health/readiness", timeout=10
                    )
                    response.raise_for_status()
                return StatusModel(status="ready")
            except httpx.RequestError as e:
                logger.error(f"Health check failed: {str(e)}")
                return FastAPIResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=f"Service not ready: {str(e)}",
                )

        @self.app.get("/topics")
        async def get_topics() -> TopicListModel:
            """Retrieve registered topics."""
            topics: TopicListModel = {"topics": []}
            for name, bot in self.bots.items():
                topics["topics"].append(
                    {
                        "endpoint": name,
                        "title": bot.name.to_json(),
                        "short_description": bot.short_description.to_json(),
                        "long_description": bot.long_description.to_json(),
                        "modules": (await get_modules(Topic(name))).modules,
                        "type": TopicType.SKILLS
                            if bot.skill_topic
                            else TopicType.BASIC,
                        "features": bot.features,
                        "priority": bot.priority,
                        "enabled": bot.enabled,
                        "color": bot.color,
                    }
                )
            return topics

        def refresh_cached_llms_with_health(models_json_path):
            """Update cached LLMs with health check information."""
            logger.info("Refreshing cached LLMs with health check information.")
            lite_llm_url = os.getenv("LITELLM_URL")
            lite_llm_key = os.getenv("LITELLM_KEY")
            ai_model_list: dict[str, LLM] = {}

            # request available models and their info from LiteLLM
            lite_llm_info_request = requests.get(
                f"{lite_llm_url}/model/info",
                headers={"Authorization": f"Bearer {lite_llm_key}"},
                timeout=10,
            )
            if lite_llm_info_request.status_code == 200:
                lite_llm_model_infos = lite_llm_info_request.json()
                for model_health in lite_llm_model_infos["data"]:
                    if (
                        "litellm_params" in model_health
                        and "model" in model_health["litellm_params"]
                    ):
                        model_id = model_health["model_info"]["id"]
                        # create a LLM object with the model info for each model
                        ai_model_list[model_id] = LLM(
                            id=model_id,
                            label=model_health["model_name"],
                            model_name=model_health["litellm_params"]["model"],
                            api_base_url=model_health["litellm_params"]["api_base"]
                            if "api_base" in model_health["litellm_params"]
                            else None,
                            status=LLMStatus.UNHEALTHY.value,
                        )

            # request the health status of the models from LiteLLM
            # does a small call to every model to check if it is healthy
            lite_llm_health_request = requests.get(
                f"{lite_llm_url}/health",
                headers={"Authorization": f"Bearer {lite_llm_key}"},
                timeout=300,
            )

            if lite_llm_health_request.status_code == 200:
                lite_llm_health = lite_llm_health_request.json()
                for model_health in lite_llm_health["healthy_endpoints"]:
                    # only check health endpoints, the rest is anyway not healthy
                    model_id = [
                        v.id
                        for v in ai_model_list.values()
                        if v.model_name == model_health["model"]
                    ]
                    if model_id and len(model_id) == 1:
                        ai_model_list[model_id[0]].status = LLMStatus.HEALTHY

            cached_llms = CachedAIModels(
                timestamp=str(datetime.now().timestamp()),
                models=list(ai_model_list.values()),
            )

            with Path.open(models_json_path, "w") as f:
                json.dump(cached_llms.model_dump(), f)
            self.cached_ai_models = cached_llms
            return cached_llms

        @self.app.get("/models")
        def get_models() -> AIModelsResponse:
            """Retrieve available LLM models with their health status."""
            chat_configuration = ChatConfig(
                max_messages_before_summarization=MAX_MESSAGES_BEFORE_SUMMARIZATION,
            )
            timestamp = datetime.now().timestamp()
            # get the purpose list from the config file
            purpose_list_model = get_ai_models()
            if purpose_list_model is None:
                return AIModelsResponse(
                    purposes=[],
                    timestamp=timestamp,
                    config=chat_configuration,
                    error="AI models configuration is invalid.",
                )
            purpose_list = purpose_list_model.purposes

            models_json_path = Path(__file__).parent.parent.parent / "models.json"

            def filter_healthy_purposes(
                purpose_list: list[PurposeConfigModel],
                available_models: list[LLM],
            ) -> list[PurposeModel]:
                """Check which purposes have at least one healthy model."""
                return_list: list[PurposeModel] = []
                healthy_models = [
                    model
                    for model in available_models
                    if model.status == LLMStatus.HEALTHY.value
                ]
                for purpose in purpose_list:
                    purpose_model = PurposeModel(
                        id=LLMPurpose(purpose.id),
                        label=purpose.label,
                        description=purpose.description,
                        icon=purpose.icon,
                        healthy=False,
                    )
                    if any(model.label in purpose.models for model in healthy_models):
                        purpose_model.healthy = True
                    return_list.append(purpose_model)
                return return_list

            def load_or_refresh_cache() -> CachedPurposes:
                """Load the cache from the file."""
                # file does not exist, so we need to refresh
                if not models_json_path.exists():
                    cached_ai_models = refresh_cached_llms_with_health(models_json_path)
                else:
                    # file exists, load the cache
                    with Path.open(models_json_path, "r") as f:
                        llms_json = json.load(f)
                        cached_ai_models = CachedAIModels.model_validate(llms_json)
                        if (
                            cached_ai_models.timestamp + MODELS_REFRESH_THRESHOLD
                            < timestamp
                        ):
                            # cache is outdated, so need to refresh
                            # perform asynchronously so it doesn't block the user
                            asyncio.create_task(
                                refresh_cached_llms_with_health(models_json_path)
                            )

                self.cached_ai_models = cached_ai_models
                return CachedPurposes(
                    purposes=filter_healthy_purposes(
                        purpose_list, cached_ai_models.models
                    ),
                    timestamp=cached_ai_models.timestamp,
                )

            # Check if cache needs to be loaded or refreshed
            need_cache_refresh = (
                self.cached_purposes is None or 
                self.cached_purposes.timestamp + MODELS_REFRESH_THRESHOLD <= timestamp
            )
            
            if need_cache_refresh:
                try:
                    self.cached_purposes = load_or_refresh_cache()
                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to decode model.json. Deleting and refreshing "
                        "cache. %s",
                        e,
                    )
                    # delete the file and refresh the cache
                    if models_json_path.exists():
                        Path.unlink(models_json_path)
                    self.cached_purposes = load_or_refresh_cache()
                except Exception as e:
                    error_message = (
                        f"Failed to load or refresh cache: {e}. "
                        "Returning empty purpose list."
                    )
                    logger.error(error_message)
                    return AIModelsResponse(
                        purposes=[],
                        timestamp=timestamp,
                        config=chat_configuration,
                        error=error_message,
                    )

            # Return the cached data (either freshly loaded or still valid)
            return AIModelsResponse(
                purposes=self.cached_purposes.purposes,
                timestamp=self.cached_purposes.timestamp,
                config=chat_configuration,
            )

        @self.app.get("/topic/{topic}/modules")
        async def get_modules(topic: Topic) -> ModulesResponse:
            """Retrieve modules of the bot."""
            if inspect.iscoroutinefunction(self.bots[topic.value].get_modules):
                # if get_modules is a coroutine, await it
                modules = await self.bots[topic.value].get_modules()
            else:
                # otherwise, call it directly
                modules = self.bots[topic.value].get_modules()
            return ModulesResponse(modules=modules)

        @self.app.get("/models/health")
        def get_models_health() -> dict[str, str]:
            """Get the health of the models."""
            # TODO update? even needed anymore?
            litellm_url = os.getenv("LITELLM_URL")
            litellm_key = os.getenv("LITELLM_KEY")
            model_info = requests.get(
                f"{litellm_url}/model/info",
                headers={"Authorization": f"Bearer {litellm_key}"},
                timeout=10,
            )
            model_info_json = model_info.json()
            model_info_json = {
                model["model_name"]: model for model in model_info_json["data"]
            }
            kisski_base_url = "https://chat-ai.academiccloud.de/v1"
            kisski_key = os.getenv("KISSKI_API_KEY")
            kisski_info = requests.get(
                f"{kisski_base_url}/models",
                headers={"Authorization": f"Bearer {kisski_key}"},
                timeout=10,
            )
            kisski_info_json = kisski_info.json()
            kisski_info_json = {
                model["id"]: model for model in kisski_info_json["data"]
            }
            models = get_models()
            health = {model.label: "healthy" for model in models.purposes}
            for model in models.purposes:
                if model.label not in model_info_json:
                    health[model.label] = "not found"
                elif model_info_json[model.label]["status"] != "healthy":
                    health[model.label] = model_info_json[model.label]["status"]
            return health

        def select_llm_by_purpose(selected_purpose: LLMPurpose) -> LLM:
            """Selects the best available LLM for the given purpose and locale.

            Args:
                selected_purpose: The purpose of the LLM (e.g., 'optimal')
                locale: Optional locale preference

            Returns:
                The ID of the selected LLM model

            """
            if not self.cached_ai_models:
                # Use the cached models with status information
                models_json_path = Path(__file__).parent.parent.parent / "models.json"
                if not models_json_path.exists():
                    logger.error("No models.json file found. Cannot select model.")
                    return None

                with Path.open(models_json_path, "r") as f:
                    self.cached_ai_models = CachedAIModels.model_validate(json.load(f))
            purpose_list_model = get_ai_models()
            purpose_list = [
                purpose
                for purpose in purpose_list_model.purposes
                if purpose.id == selected_purpose.value
            ]
            healthy_models = [
                model
                for model in self.cached_ai_models.models
                if model.status == LLMStatus.HEALTHY.value
            ]
            if purpose_list:
                purpose = purpose_list[0]
                # Check if the purpose has any models
                if purpose.models and len(purpose.models) > 0:
                    # Check if the purpose has any healthy models
                    for model in purpose.models:
                        model_objs = [m for m in healthy_models if m.label == model]
                        for model_obj in model_objs:
                            return model_obj

            # If no model from selected purpose is available, get first available model
            for model in healthy_models:
                return model

            # If no model is available, return None
            logger.error("No available healthy models found")
            return None

        def modify_request(topic: Topic, request: RequestModel) -> RequestModel:
            # If llm_purpose is provided, select appropriate LLM model
            if (
                Features.AIMODEL in self.bots[topic.value].features
                and request.llm_purpose
            ):
                model = select_llm_by_purpose(request.llm_purpose)
                if model:
                    # Create a LLM object with the selected model ID
                    request.llm = model
                    logger.info(
                        "Selected model %s for purpose %s",
                        model.label,
                        request.llm_purpose,
                    )
                else:
                    logger.error(
                        "Could not find suitable model for purpose %s",
                        request.llm_purpose,
                    )
            return request

        @self.app.post("/topic/{topic}")
        async def init_chat(topic: Topic, request: RequestModel) -> Response:
            return await self.bots[topic.value].init_chat(
                modify_request(topic, request)
            )

        @self.app.post("/topic/{topic}/message")
        async def chat_invoke(topic: Topic, request: RequestModel) -> Response:
            return await self.bots[topic.value].chat_invoke(
                modify_request(topic, request)
            )

        @self.app.post("/topic/{topic}/title")
        async def update_title(
            topic: Topic, request: RequestModel
        ) -> TitleResponse:
            return await self.bots[topic.value].update_title(
                modify_request(topic, request)
            )

        @self.app.post("/topic/{topic}/summarize")
        async def summarize(
            topic: Topic, request: RequestModel
        ) -> SummaryResponse:
            """Summarize the chat history asynchronously."""
            return await self.bots[topic.value].summarize(
                modify_request(topic, request)
            )

        @self.app.post("/topic/{topic}/{endpoint}", response_model=None)
        async def action_callback(
            topic: Topic, endpoint: str, request: RequestModel
        ) -> Response | StreamingResponse:
            if endpoint not in self.bots[topic.value]._routes:
                return Response.from_message(
                    f"Action {endpoint} not found in bot {topic.value}."
                )
            return await self.bots[topic.value]._routes[endpoint](request)

        @self.app.get("/learning_types/from_personality/{personality_type}")
        def convert_personality_type(
            personality_type: PersonalityType,
        ) -> PersonalityTypeConversionResponse:
            """Convert personality type to learning type."""
            pt_to_lt = {
                PersonalityType.ISTJ: AvailableLearningTypes.SENSING,
                PersonalityType.ISFJ: AvailableLearningTypes.SENSING,
                PersonalityType.ESTP: AvailableLearningTypes.SENSING,
                PersonalityType.ESFP: AvailableLearningTypes.SENSING,
                PersonalityType.INFJ: AvailableLearningTypes.INTUITIVE,
                PersonalityType.INTJ: AvailableLearningTypes.INTUITIVE,
                PersonalityType.ENFP: AvailableLearningTypes.INTUITIVE,
                PersonalityType.ENTP: AvailableLearningTypes.INTUITIVE,
                PersonalityType.ISTP: AvailableLearningTypes.THINKING,
                PersonalityType.INTP: AvailableLearningTypes.THINKING,
                PersonalityType.ESTJ: AvailableLearningTypes.THINKING,
                PersonalityType.ENTJ: AvailableLearningTypes.THINKING,
                PersonalityType.ISFP: AvailableLearningTypes.FEELING,
                PersonalityType.INFP: AvailableLearningTypes.FEELING,
                PersonalityType.ESFJ: AvailableLearningTypes.FEELING,
                PersonalityType.ENFJ: AvailableLearningTypes.FEELING,
            }
            try:
                if personality_type not in pt_to_lt:
                    return {"error": "Personality type not found"}
                result = pt_to_lt.get(personality_type, None)
                return {"learning_type": result.value}
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.exception(e)
                return {"error": str(e), "traceback": error_traceback}

        @self.app.post("/admin/configure")
        def set_bots_disabled(
            configuration: ConfigureTopicsRequest,
        ) -> ConfigureTopicsResponse:
            if not configuration.validate_key():
                return ConfigureTopicsResponse(
                    success=False, error_message="Invalid key."
                )
            for bot in self.bots.values():
                if bot.id in configuration.enabled:
                    bot.enabled = configuration.enabled[bot.id]
            return ConfigureTopicsResponse(success=True)

        @self.app.post("/admin/config")
        def update_config(
            config_update: ConfigUpdateRequest,
        ) -> ConfigureTopicsResponse:
            """Update the configuration file with new values."""
            if not config_update.validate_key():
                return ConfigureTopicsResponse(
                    success=False, error_message="Invalid key."
                )

            try:
                # Get current config
                current_config = config.get_config()

                # Validate that all keys in updates exist in the current config
                for key in config_update.updates:
                    if key not in current_config:
                        return ConfigureTopicsResponse(
                            success=False, error_message=f"Config key not found: {key}"
                        )

                # Update the config
                config.save_config(config_update.updates)

                return ConfigureTopicsResponse(success=True)
            except Exception as e:
                return ConfigureTopicsResponse(
                    success=False, error_message=f"Error updating config: {str(e)}"
                )

        @self.app.get("/admin/config")
        def get_config_by_key(key: str = None) -> ConfigReadResponse:
            """Get the current configuration values using query parameter."""
            if not key:
                return ConfigReadResponse(
                    success=False, error_message="Missing key parameter."
                )

            admin_request = AdminRequest(key=key)
            if not admin_request.validate_key():
                return ConfigReadResponse(success=False, error_message="Invalid key.")

            try:
                # Instead of accessing individual attributes, get the entire config
                config_values = config.get_config()
                return ConfigReadResponse(success=True, config=config_values)
            except Exception as e:
                return ConfigReadResponse(
                    success=False, error_message=f"Error reading config: {str(e)}"
                )

    def register_bot(self, bot: BaseBot) -> None:
        """Register a bot with the router before the app has received any requests.

        This function gathers all the routes from the bot and adds them to the Flask
        app. At the moment, it adds all routes as POST requests, but this could be
        extended to support other HTTP methods if needed.
        """
        if bot.id in self.bots:
            raise ValueError(
                f"Bot {bot.id} already registered. "
                "Remove it before registering a new bot."
            )
        logger.info(f"{bot.name} - Registered bot with route /{bot.id}")
        self.bots[bot.id] = bot
        if bot.router:
            self.app.include_router(bot.router)


def get_ai_models() -> PurposeListConfigModel:
    """Get the AI models from the configuration."""
    try:
        validated = PurposeListConfigModel.model_validate(AI_MODELS)
        return validated
    except ValidationError as e:
        logger.error(f"Error validating AI models: {e}")
        return None
