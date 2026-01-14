import inspect
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path as PathLib

import requests
from fastapi import Depends, FastAPI, HTTPException, Path, status
from fastapi import Response as FastAPIResponse
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from framework.db.db_types import PurposeDB

sys.path.append(str(PathLib(__file__).parent.parent))
from bots.study.helpers.helpers import get_ai_models
from bots.study.helpers.models import (
    FeedbackRequest,
    InspirationsResponse,
    PlanResponse,
)
from framework import config
from framework.api_types.admin import (
    AdminRequest,
    ConfigReadResponse,
    ConfigUpdateRequest,
    ConfigureTopicsRequest,
    ConfigureTopicsResponse,
    RefreshScadsBotsResponse,
)
from framework.api_types.ai_models import (
    AIModelsResponse,
    ChatConfig,
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
from framework.api_types.quiz_models import (
    InitialQuizAnswersRecommendation,
    InitialQuizAnswersRequest,
    InitialQuizModel,
    QuizAnswersRequest,
    QuizCompletionRequest,
    QuizCompletionResponse,
    QuizModel,
    QuizQuestionEvaluationRequest,
    QuizQuestionEvaluationResponse,
)
from framework.api_types.request_format import (
    CommentRequestModel,
    MessageVoteRequest,
    RequestModel,
)
from framework.api_types.response_format import (
    CommentResponse,
    ErrorReport,
    MessageVoteResponse,
    Response,
    SummaryResponse,
    TitleResponse,
)
from framework.api_types.topics import TopicListModel
from framework.config import get_config

logger = logging.getLogger()


class Router:
    """Router for handling requests to the API."""

    def __init__(self, app: FastAPI) -> None:
        """Initialize the router."""
        self.app: FastAPI = app
        self.bots: dict = {}

        def validate_topic(
            topic: str = Path(..., description="Bot topic identifier")
        ) -> str:
            """Validate that the topic exists in registered bots."""
            if topic not in self.bots:
                raise HTTPException(
                    status_code=404,
                    detail=f"Topic '{topic}' not found. Available topics: {
                        list(self.bots.keys())
                    }"
                )
            return topic

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
                api_key = os.getenv("LITELLM_KEY")
                client = OpenAI(api_key=api_key, base_url=base_url)
                models = client.models.list()
                if not models:
                    logger.error("Health check failed: No models found")
                    return FastAPIResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content="LLM service not ready: No models found",
                    )
                return StatusModel(status="ready")
            except Exception as e:
                # If any dependency checks fail, return a 503 status code
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
                        "modules": (await get_modules(name)).modules,
                        "type": bot.bot_type.value,
                        "features": bot.features,
                        "priority": bot.priority,
                        "optional": bot.optional,
                        "enabled": bot.enabled,
                        "color": bot.color,
                        "avatar": bot.avatar,
                        "tag": bot.tag,
                    }
                )
            return topics

        @self.app.get("/models")
        async def get_models() -> AIModelsResponse:
            """Retrieve available LLM models with their health status."""
            max_msgs_b4_summarization = await get_config(
                "MAX_MESSAGES_BEFORE_SUMMARIZATION"
            )
            chat_configuration = ChatConfig(
                max_messages_before_summarization=int(max_msgs_b4_summarization),
            )
            timestamp = datetime.now().timestamp()

            # get the purpose list from the config file
            purpose_list_model = await get_ai_models()
            if purpose_list_model is None:
                return AIModelsResponse(
                    purposes=[],
                    timestamp=timestamp,
                    config=chat_configuration,
                    error="AI models configuration is invalid.",
                )

            purpose_list = [
                PurposeModel(
                    id=purpose.id,
                    label=purpose.label,
                    description=purpose.description,
                    icon=purpose.icon,
                    healthy=len(purpose.label.values()) > 0,  # if no label, don't show
                )
                for purpose in purpose_list_model.purposes
            ]

            # Return the cached data (either freshly loaded or still valid)
            return AIModelsResponse(
                purposes=purpose_list,
                timestamp=timestamp,
                config=chat_configuration,
            )

        @self.app.get("/topic/{topic}/modules")
        async def get_modules(
            topic: str = Depends(validate_topic)
        ) -> ModulesResponse:
            """Retrieve modules of the bot."""
            if inspect.iscoroutinefunction(self.bots[topic].get_modules):
                # if get_modules is a coroutine, await it
                modules = await self.bots[topic].get_modules()
            else:
                # otherwise, call it directly
                modules = self.bots[topic].get_modules()
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

        def modify_request(topic: str, request: RequestModel) -> RequestModel:
            return request

        @self.app.post("/topic/{topic}", response_model=None)
        async def init_chat(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> Response | StreamingResponse:
            try:
                return await self.bots[topic].init_chat(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while initializing chat: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())

                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "init_chat",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/message")
        async def chat_invoke(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> Response:
            try:
                return await self.bots[topic].chat_invoke(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while invoking chat: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())

                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "chat_invoke",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/title")
        async def update_title(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> TitleResponse:
            try:
                return await self.bots[topic].update_title(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while updating title: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return TitleResponse(
                    title="",
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "update_title",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/inspiration")
        async def inspiration(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> InspirationsResponse:
            try:
                return await self.bots[topic].inspirations(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while fetching inspirations: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return InspirationsResponse(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "inspirations",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/message/comment")
        async def comment(
            request: CommentRequestModel, topic: str = Depends(validate_topic)
        ) -> CommentResponse:
            try:
                return await self.bots[topic].comment(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while fetching comments: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return CommentResponse(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "comment",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/message/vote")
        async def vote(
            request: MessageVoteRequest, topic: str = Depends(validate_topic)
        ) -> MessageVoteResponse:
            try:
                return await self.bots[topic].vote_message(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while fetching comments: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return CommentResponse(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "vote",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/quiz", response_model=None)
        async def quiz(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> QuizModel | StreamingResponse:
            try:
                return await self.bots[topic].quiz(modify_request(topic, request))
            except Exception as e:
                logger.error("Error occurred while fetching quiz: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return QuizModel(
                    id="",
                    title="",
                    description="",
                    questions=[],
                    score=(0, 0),
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "quiz",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/initial_quiz")
        async def initial_quiz(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> InitialQuizModel:
            try:
                return await self.bots[topic].initial_quiz(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while fetching initial quiz: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return InitialQuizModel(
                    id="",
                    title="",
                    description="",
                    questions=[],
                    score=(0, 0),
                    quiz_questions_asked_per_level=(0, 0, 0),
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "initial_quiz",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/answer_initial_quiz")
        async def answer_initial_quiz(
            request: InitialQuizAnswersRequest, 
            topic: str = Depends(validate_topic)
        ) -> InitialQuizAnswersRecommendation:
            try:
                return await self.bots[topic].answer_initial_quiz(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while fetching initial quiz: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return InitialQuizAnswersRecommendation(
                    quiz_performance_below=0,
                    quiz_performance_at_level=0,
                    quiz_performance_above=0,
                    quiz_recommended_change=0,
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "answer_initial_quiz",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.put("/topic/{topic}/quiz")
        async def answer_quiz(
            request: QuizAnswersRequest, topic: str = Depends(validate_topic)
        ) -> Response:
            try:
                return await self.bots[topic].answer_quiz(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while answering quiz: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "answer_quiz",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/quiz/evaluate")
        async def evaluate_quiz_question(
            request: QuizQuestionEvaluationRequest, 
            topic: str = Depends(validate_topic)
        ) -> QuizQuestionEvaluationResponse:
            try:
                return await self.bots[topic].evaluate_quiz_question(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while evaluating quiz question: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return QuizQuestionEvaluationResponse(
                    score=0,
                    max_score=0,
                    is_correct=False,
                    solution="Error",
                    feedback=f"An error occurred while evaluating the answer: {str(e)}",
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "evaluate_quiz_question",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/quiz/complete")
        async def complete_quiz(
            request: QuizCompletionRequest, topic: str = Depends(validate_topic)
        ) -> QuizCompletionResponse:
            try:
                return await self.bots[topic].complete_quiz(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while completing quiz: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return QuizQuestionEvaluationResponse(
                    score=0,
                    max_score=0,
                    is_correct=False,
                    solution="Error",
                    feedback=f"An error occurred while completing the quiz: {str(e)}",
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "complete_quiz",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/feedback")
        async def feedback(
            request: FeedbackRequest, topic: str = Depends(validate_topic)
        ) -> Response:
            try:
                return await self.bots[topic].feedback(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while sending feedback: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "feedback",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )
            try:
                return await self.bots[topic].feedback(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while sending feedback: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "feedback",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/plan-session")
        async def plan_session(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> PlanResponse:
            try:
                return await self.bots[topic].plan_session(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while planning session: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return PlanResponse(
                    recommended_topics=[],
                    recommended_date="",
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "plan_session",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/summarize")
        async def summarize(
            request: RequestModel, topic: str = Depends(validate_topic)
        ) -> SummaryResponse:
            """Summarize the chat history asynchronously."""
            try:
                return await self.bots[topic].summarize(
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while summarizing chat history: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return SummaryResponse(
                    summary="",
                    keep_last_messages_until=-1,
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": "summarize",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )

        @self.app.post("/topic/{topic}/{endpoint}", response_model=None)
        async def action_callback(
            endpoint: str, request: RequestModel, 
            topic: str = Depends(validate_topic)
        ) -> Response | StreamingResponse:
            if endpoint not in self.bots[topic]._routes:
                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=f"Action {endpoint} not found in bot {topic}.",
                        context={
                            "method": f"{endpoint}",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )
            try:
                response = await self.bots[topic]._routes[endpoint](
                    modify_request(topic, request)
                )
            except Exception as e:
                logger.error("Error occurred while calling action endpoint: %s", e)
                logger.error("Traceback: %s", traceback.format_exc())
                return Response(
                    messages=[],
                    error=ErrorReport(
                        error=str(e),
                        context={
                            "method": f"{endpoint}",
                            "timestamp": datetime.now().isoformat(),
                            "topic": topic,
                            "request": request.model_dump(),
                        },
                    ),
                )
            return response

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
        async def update_config(
            config_update: ConfigUpdateRequest,
        ) -> ConfigureTopicsResponse:
            """Update the configuration file with new values."""
            if not config_update.validate_key():
                return ConfigureTopicsResponse(
                    success=False, error_message="Invalid key."
                )

            try:
                if "AI_MODELS" in config_update.updates.keys():
                    ai_models = config_update.updates.get("AI_MODELS", {})
                    if not isinstance(ai_models, dict) or "purposes" not in ai_models:
                        return ConfigureTopicsResponse(
                            success=False,
                            error_message="Invalid AI_MODELS structure.",
                        )
                    # Further validation can be added here as needed
                    for purpose in ai_models["purposes"]:
                        pur: PurposeDB | None = await config.get_purpose(
                            purpose.get("code")
                        )
                        if not pur:
                            return ConfigureTopicsResponse(
                                success=False,
                                error_message=(
                                    f"Purpose not found: {purpose.get('code')}"
                                ),
                            )
                        if pur.models != purpose.get("models", []):
                            await config.save_purpose(
                                PurposeDB(
                                    idpurposes=pur.idpurposes,
                                    code=purpose.get("code", pur.code),
                                    icon=purpose.get("icon", pur.icon),
                                    models=purpose.get("models", pur.models),
                                    enabled=purpose.get("enabled", pur.enabled),
                                )
                            )
                    return ConfigureTopicsResponse(success=True)
                # Get current config
                current_config = await config.get_config()

                # Validate that all keys in updates exist in the current config
                for key in config_update.updates:
                    if key not in current_config:
                        return ConfigureTopicsResponse(
                            success=False, error_message=f"Config key not found: {key}"
                        )

                # Update the config
                await config.save_config(config_update.updates)

                return ConfigureTopicsResponse(success=True)
            except Exception as e:
                return ConfigureTopicsResponse(
                    success=False, error_message=f"Error updating config: {str(e)}"
                )

        @self.app.get("/admin/config")
        async def get_config_by_key(key: str = None) -> ConfigReadResponse:
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
                config_values = await config.get_config()
                purposes = await config.get_all_purposes()
                return ConfigReadResponse(
                    success=True,
                    config=config_values,
                    purposes={p.code: p for p in purposes},
                )
            except Exception as e:
                return ConfigReadResponse(
                    success=False, error_message=f"Error reading config: {str(e)}"
                )

        @self.app.post("/admin/refresh-scads-bots")
        async def refresh_scads_bots(
            request: AdminRequest,
        ) -> RefreshScadsBotsResponse:
            """Refresh ScaDS.AI assistant bots from the external API."""
            if not request.validate_key():
                return RefreshScadsBotsResponse(
                    success=False, error_message="Invalid key."
                )

            try:
                from bots.scads.scads_factory import scads_factory

                # Get current ScaDS bot IDs
                old_scads_bot_ids = {
                    bot_id for bot_id in self.bots.keys()
                    if bot_id.startswith("scads_")
                }

                # Clear cache and fetch new bots
                scads_factory.clear_cache()
                new_bots = scads_factory.create_all_bots_sync()
                new_scads_bot_ids = {bot.id for bot in new_bots}

                # Find added and removed bots
                bots_added = list(new_scads_bot_ids - old_scads_bot_ids)
                bots_removed = list(old_scads_bot_ids - new_scads_bot_ids)

                # Remove old ScaDS bots
                for bot_id in old_scads_bot_ids:
                    if bot_id in self.bots:
                        del self.bots[bot_id]

                # Register new bots
                for bot in new_bots:
                    self.bots[bot.id] = bot
                    logger.info(f"Refreshed ScaDS bot: {bot.id}")

                return RefreshScadsBotsResponse(
                    success=True,
                    bots_added=bots_added,
                    bots_removed=bots_removed,
                    total_bots=len(new_bots),
                )
            except Exception as e:
                logger.error(f"Error refreshing ScaDS bots: {e}")
                return RefreshScadsBotsResponse(
                    success=False, error_message=f"Error: {str(e)}"
                )

    def register_bot(self, bot) -> None:
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

