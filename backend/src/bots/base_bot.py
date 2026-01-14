import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Union

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableSerializable
from langfuse import Langfuse, get_client
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))
from bots.study.helpers.models import (
    FeedbackRequest,
    InspirationsResponse,
    PlanResponse,
)
from framework.api_types.choice import (
    ChatCompletionsChunk,
    Choice,
    ChoiceDelta,
    MessageEvent,
)
from framework.api_types.learning_type import LearningTypeModel
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.module import Module, Skill
from framework.api_types.quiz_models import (
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
    Message,
    MessageType,
    MessageVoteRequest,
    RequestModel,
)
from framework.api_types.response_format import (
    CommentResponse,
    MessageResponse,
    MessageVoteResponse,
    Response,
    Source,
    TitleResponse,
)
from framework.chains.passthrough_chain import PassthroughChain
from framework.config import get_config
from framework.db.database import Database
from framework.llm.lite_llm import LiteLLM
from framework.rag.embeddings.base_embedding import BaseEmbedding
from framework.rag.vector_dbs.pgvector import PGVectorDB

logger = logging.getLogger()
langfuse = get_client()


class SummaryResult(BaseModel):
    """Result of the summarization."""

    messages: list[Message]
    includes_summary: bool
    summary: str | None


class ResponseGenerationData(BaseModel):
    """Model for transporting data for generating chat responses."""

    chain_config: dict
    created_chain: RunnableSerializable
    sources: dict[int, Source]
    llm_model: str
    storage: dict | None = None
    metadata_information: dict | None = None


class TopicType(Enum):
    """Enumeration of topic types."""

    SKILLS = "skills"
    BASIC = "basic"
    COACH = "coach"


class Features(Enum):
    """Features of the bot."""

    TITLE = "title"  # Generate a title for the conversation
    INSPIRATIONS = "inspirations"  # Generate inspiration messages for the user
    INITIATIVE = "initiative"  # Give over initiative to the bot
    INITIAL_QUIZ = "initial_quiz"  # Generate initial quiz to test the user's knowledge
    QUIZ = "quiz"  # Generate quiz to test the user's knowledge
    FEEDBACK = "feedback"  # Provide feedback on the bot's performance
    PLAN = "plan"  # Plan the next session
    STREAMING = "streaming"  # Enable streaming responses
    SUMMARY = "summary"  # Generate automatic summaries if the conversation is long
    AIMODEL = "aimodel"  # Let the user select the AI model to use for the conversation
    SCIENTIFIC_PAPER_CONTEXT = (
        "scientific_paper_context"  # Enable the scientific paper context sidebar
    )
    WIP = "wip"  # Work in progress feature
    DASHBOARD = "dashboard"  # Enable side dashboard in chat


class BaseBot(ABC):
    """A chat bot that can be used to chat with the user."""

    DISABLE_STREAMING = True
    router: APIRouter
    db: Database

    def __init__(
        self,
        identifier: str,
        name: LocalizedString,
        short_description: LocalizedString,
        long_description: LocalizedString,
        embeddings: BaseEmbedding,
        bot_type: TopicType = TopicType.BASIC,
        features: List[Features] = None,
        priority: int = 0,
        optional: bool = True,
        enabled: bool = True,
        color: str = "#000000",
        avatar: str = None,
        tag: str = None,
    ) -> None:
        """Initialize the chat bot."""
        self.id = identifier
        self.name = name
        self.short_description = short_description
        self.long_description = long_description
        self.bot_type = bot_type
        self._routes = {}
        self.router = APIRouter(prefix=f"/topic/{self.id}")
        self.features = features if features is not None else []
        self._decorated_functions = {}
        self.priority = priority
        self.optional = optional
        self.enabled = enabled
        self.color = color
        self.embeddings = embeddings
        self.db = None
        self.vector_store = None
        self.avatar = avatar
        self.tag = tag

        def post(path: str):
            """Add a POST route to the bot's additional endpoints."""

            def decorator(func):
                self._routes[path.lstrip("/")] = func
                return func

            return decorator

        self.post = post

    def get_router(self) -> APIRouter:
        """Get the router of the bot."""
        return self.router

    async def ainit_db_connection(self) -> None:
        """Asynchronous initialization of the vector db connection."""
        if self.db is None:
            self.db = Database()
        if self.db.connection is None:
            await self.db.connect()
        if self.vector_store is None:
            self.vector_store = PGVectorDB(self.embeddings, self.db, table_name="chunk")
            await self.vector_store.ainit()
            await self.vector_store.apply_index()

    async def get_vector_store(self) -> PGVectorDB:
        """Get the vector store for the study competence bot.

        This method initializes the vector store if it is not already set and returns
        the vector store instance. It ensures that the database connection is
        established before returning the vector store.

        Args:
            None
        Returns:
            VectorStore: The initialized vector store instance.

        """
        if self.vector_store is None:
            await self.ainit_db_connection()
        return self.vector_store

    async def get_db(self) -> Database:
        """Get the database connection for the study competence bot.

        This method returns the database instance used by the bot. It ensures that the
        database connection is established before returning the instance.

        Args:
            None
        Returns:
            Database: The initialized database instance.

        """
        if self.db is None:
            await self.ainit_db_connection()
        return self.db

    @abstractmethod
    def get_modules(self) -> List[Union[Module, Skill]]:
        """Get the modules of the bot."""

    @abstractmethod
    async def init_chat(self, request: RequestModel) -> Response | StreamingResponse:
        """Initialize the chat with the bot."""

    @abstractmethod
    async def chat_invoke(self, request: RequestModel) -> Response | StreamingResponse:
        """Chat with the bot."""

    async def chat_stream(self, request: RequestModel) -> StreamingResponse:
        """Chat with the bot through streaming."""
        if not self.features or Features.STREAMING not in self.features:
            raise NotImplementedError("Streaming feature not implemented.")

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate a title for the given conversation."""
        if not self.features or Features.TITLE not in self.features:
            raise NotImplementedError("Title feature not implemented.")

    async def inspirations(self, request: RequestModel) -> InspirationsResponse:
        """Generate a list of inspirations for the given conversation."""
        if not self.features or Features.INSPIRATIONS not in self.features:
            raise NotImplementedError("Inspirations feature not implemented.")

    async def quiz(self, request: RequestModel) -> QuizModel | StreamingResponse:
        """Generate a quiz given the conversation."""
        if not self.features or Features.QUIZ not in self.features:
            raise NotImplementedError("Quiz feature not implemented.")

    async def initial_quiz(self, request: RequestModel) -> InitialQuizModel:
        """Generate an initial assessment quiz."""
        if not self.features or Features.INITIAL_QUIZ not in self.features:
            raise NotImplementedError("Initial quiz feature not implemented.")

    async def feedback(self, request: FeedbackRequest) -> Response:
        """Provide feedback on the bot's performance."""
        if not self.features or Features.FEEDBACK not in self.features:
            raise NotImplementedError("Feedback feature not implemented.")

    async def plan_session(self, request: RequestModel) -> PlanResponse:
        """Plan the next session."""
        if not self.features or Features.PLAN not in self.features:
            raise NotImplementedError("Plan feature not implemented.")

    async def answer_quiz(self, request: QuizAnswersRequest) -> Response:
        """Submit the answers to a quiz."""
        if not self.features or Features.QUIZ not in self.features:
            raise NotImplementedError("Quiz feature not implemented.")

    async def evaluate_quiz_question(
        self, request: QuizQuestionEvaluationRequest
    ) -> QuizQuestionEvaluationResponse:
        """Evaluate a single quiz question answer."""
        if not self.features or Features.QUIZ not in self.features:
            raise NotImplementedError("Quiz evaluation feature not implemented.")

    async def complete_quiz(
        self, request: QuizCompletionRequest
    ) -> QuizCompletionResponse:
        """Evaluate a single quiz question answer."""
        if not self.features or Features.QUIZ not in self.features:
            raise NotImplementedError("Quiz evaluation feature not implemented.")

    async def answer_initial_quiz(self, request: InitialQuizAnswersRequest) -> Response:
        """Submit the answers to an initial quiz."""
        if not self.features or Features.INITIAL_QUIZ not in self.features:
            raise NotImplementedError("Initial quiz feature not implemented.")

    async def summarize(self, request: RequestModel) -> Response:
        """Summarize the chat history asynchronously.

        This method is called by the frontend during idle periods to summarize long
        conversations without blocking the main chat interaction.
        """
        if not self.features or Features.SUMMARY not in self.features:
            raise NotImplementedError("Summary feature not implemented.")

    async def comment(self, request: CommentRequestModel) -> CommentResponse:
        """Add a comment to a specific message in the chat.

        This method allows users to add comments to individual messages within the
        chat history for better context and understanding.

        Args:
            request (CommentRequestModel): The request containing the message ID and
                the comment text.

        Returns:
            CommentResponse: The response confirming the comment addition.

        """
        langfuse = get_client()
        langfuse.create_score(
            trace_id=request.trace_id,
            name="message-comment",
            value=request.vote if request.vote is not None else -1,
            comment=request.comment,
        )
        return CommentResponse(success=True)

    async def vote_message(self, request: MessageVoteRequest) -> MessageVoteResponse:
        """Vote on a specific message in the chat.

        This method allows users to upvote or downvote individual messages within the
        chat history to provide feedback on the quality of the responses.

        Args:
            request (MessageVoteRequest): The request containing the message ID and
                the vote value.

        Returns:
            MessageVoteResponse: The response confirming the vote addition.

        """
        langfuse = get_client()
        langfuse.create_score(
            trace_id=request.trace_id,
            name="message-vote",
            value=request.vote,
        )
        return MessageVoteResponse(success=True)

    @staticmethod
    def _pretty_name(name):
        return name.replace("_", " ")

    @staticmethod
    def get_learning_type_description(
        llm: LiteLLM, learning_type: LearningTypeModel, locale: LocaleType
    ) -> str:
        """Get the description of the learning type."""
        return llm.get_langfuse_prompt(
            name=f"learning_type_description-{learning_type.id.value.lower()}-{locale.value.lower()}",
            label="latest",
            prompt_type="text",
        ).format()

    async def summarize_chat(
        self, request: RequestModel, llm_client: LiteLLM
    ) -> SummaryResult:
        """Summarize the chat."""
        includes_summary = False
        messages = request.chat_history
        messages_since_last_summary = messages
        previous_summary = None

        max_msgs_b4_sum = await get_config("MAX_MESSAGES_BEFORE_SUMMARIZATION")
        keep_last_msgs_until = await get_config("KEEP_LAST_MESSAGES_UNTIL")

        # go through the messages last max_messages and find the last summary
        for i in range(max(len(messages) - int(max_msgs_b4_sum), 0), len(messages)):
            if hasattr(messages[i], "summary") and messages[i].summary:
                # if the message has a summary, add it to the
                # messages_since_last_summary plus the following messages
                # and break the loop
                messages_since_last_summary = [
                    Message(
                        content=messages[i].summary,
                        type="assistant",
                        timestampe=messages[i].timestamp,
                    )
                ] + messages[i + 1 :]
                includes_summary = True
                previous_summary = messages[i].summary
                break

        # if the number of messages since the last summary is greater than
        # the max_messages_to_keep, trim the messages by summarizing the last
        # max_messages_to_keep messages
        if len(messages_since_last_summary) > int(max_msgs_b4_sum):
            trimmed_messages = messages_since_last_summary[: -int(keep_last_msgs_until)]

            label = (
                "latest"
                if os.getenv("ENVIRONMENT", "development") == "development"
                else "production"
            )
            summarization_prompt = llm_client.get_langfuse_prompt(
                "competence-summarization-" + request.locale().value.lower(),
                chat=trimmed_messages,
                label=label,
                prompt_type="chat",
            )
            summary_text = {
                LocaleType.EN: "Update the following summary with the new information.",
                LocaleType.DE: (
                    "Aktualisiere die folgende Zusammenfassung mit der neuen "
                    "Information."
                ),
            }[request.locale()] + "\n"

            chain = PassthroughChain().create_chain(
                llm_client.llm(), summarization_prompt
            )
            summary = await chain.ainvoke(
                {
                    "previous_summary": summary_text + previous_summary
                    if previous_summary
                    else ""
                }
            )
            return SummaryResult(
                messages=[
                    Message(
                        content=summary,
                        type="assistant",
                        timestamp=trimmed_messages[-1].timestamp,
                    )
                ]
                + messages_since_last_summary[-int(keep_last_msgs_until) :],
                includes_summary=True,
                summary=summary,
            )
        else:
            return SummaryResult(
                messages=messages_since_last_summary,
                includes_summary=includes_summary,
                summary=None,
            )

    async def parse_response_content(self, response_dict) -> MessageResponse:
        """Parse the not-streamed message from the response dictionary.

        Checks if response contains reasoning content.
        """
        response = response_dict.get("answer", "")
        if "additional_kwargs" in response_dict:
            thoughts = response_dict["additional_kwargs"].get("reasoning_content", "")

        # Check if the response contains a thought process
        if "</think>" in response:
            split = response.split("</think>")
            response = split[1]
            thoughts = split[0].replace("<think>", "")

        message_response = MessageResponse(
            content=response,
            thoughts=thoughts,
        )

        return message_response

    async def stream_message(
        self, request: RequestModel, data: Union[ResponseGenerationData, Response]
    ):
        """Stream a message to the client.

        This method streams a message to the frontend, by yielding data in the format
        expected by the frontend for real-time updates. If a response is provided, it
        sends the message immediately. If a conversation model is provided, it starts a
        generation and streams the message content in chunks.

        Args:
            request (RequestModel): The incoming request containing user and session
                data.
            data (Union[ResponseGenerationData, Response]): The response or response
                generation data.

        Returns:
            Async generator yielding message chunks as strings.

        """
        chunk_id = f"{request.find_store('chat_id', '1')}-{request.id}"
        predefined_trace_id = Langfuse.create_trace_id(seed=chunk_id)

        if isinstance(data, Response):
            # if we got a response that we should send through the stream,
            # simply send the full message
            for message in data.messages:
                # Create a delta for each message
                delta = ChoiceDelta()
                if message.thoughts:
                    delta.thoughts = message.thoughts
                if message.content:
                    delta.content = message.content
                if message.meta_information:
                    if message.meta_information.llm_model:
                        delta.llm_model = message.meta_information.llm_model
                    if message.meta_information.sources:
                        delta.sources = message.meta_information.sources
                if message.buttons:
                    delta.buttons = message.buttons
                if message.type:
                    delta.type = message.type

                data_chunk = ChatCompletionsChunk(
                    id=chunk_id,
                    choices=[
                        Choice(
                            delta=delta,
                            finish_reason="",
                        )
                    ],
                    created=datetime.now().isoformat(),
                )

                # send message
                yield f"data: {data_chunk.model_dump_json()}\n\n"

            # send stop after all messages were processed
            final_chunk = ChatCompletionsChunk(
                id=chunk_id,
                choices=[Choice(delta=ChoiceDelta(), finish_reason="stop")],
                created=datetime.now().isoformat(),
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            return

        data: ResponseGenerationData = data
        created_chain: RunnableSerializable = data.created_chain
        chain_config = data.chain_config

        # treat sources
        # truncate source content if too long
        if data.sources:
            for source_id, source in data.sources.items():
                if len(source.chunk) > 1000:
                    # truncate content to 1000 characters
                    data.sources[source_id].chunk = (
                        source.chunk[:1000] + "... [truncated]"
                    )

        event = MessageEvent(
            timestamp=datetime.now().isoformat(),
            event="initial_metadata",
            additional_info=data.metadata_information,
        )
        # Send initial metadata
        second_chunk = ChatCompletionsChunk(
            id=chunk_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(
                        type=MessageType.ASSISTANT.value,
                        sources=data.sources,
                        llm_model=data.llm_model,
                        instructions=[f"info: {event.model_dump_json()}"],
                        storage=data.storage or None,
                        trace_id=predefined_trace_id,
                    ),
                    finish_reason="",
                )
            ],
            created=datetime.now().isoformat(),
        )
        yield f"data: {second_chunk.model_dump_json()}\n\n"

        fa_event = MessageEvent(
            timestamp=datetime.now().isoformat(),
            event="formulate_answer",
            additional_info={},
        )
        second_chunk = ChatCompletionsChunk(
            id=chunk_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(
                        type=MessageType.ASSISTANT.value,
                        instructions=[f"info: {fa_event.model_dump_json()}"],
                        storage=data.storage or None,
                    ),
                    finish_reason="",
                )
            ],
            created=datetime.now().isoformat(),
        )
        yield f"data: {second_chunk.model_dump_json()}\n\n"

        with langfuse.start_as_current_observation(
            as_type="span",
            name="kira-lead-agent",
            trace_context={"trace_id": predefined_trace_id},
        ) as span:
            # Stream message content
            token_stream_iterator = created_chain.astream(chain_config)
            message = ""  # build message content

            async for token in token_stream_iterator:
                answer = None
                reasoning_content = None
                citations = None
                instructions = None
                thought = ""
                if isinstance(token, dict):
                    if "answer" in token:
                        answer = token["answer"] or ""
                    if "additional_kwargs" in token:
                        reasoning_content = token["additional_kwargs"].get(
                            "reasoning_content", ""
                        )
                    if "citations" in token:
                        citations = token["citations"] or []
                elif isinstance(token, str):
                    # Try to parse as JSON first, in case it's a serialized dictionary
                    try:
                        parsed_token = json.loads(token)
                        if isinstance(parsed_token, dict):
                            if "answer" in parsed_token:
                                answer = parsed_token["answer"] or ""
                            if "additional_kwargs" in parsed_token:
                                reasoning_content = parsed_token[
                                    "additional_kwargs"
                                ].get("reasoning_content", "")
                            if "citations" in parsed_token:
                                citations = parsed_token["citations"] or []
                        else:
                            answer = message + token
                    except (json.JSONDecodeError, TypeError):
                        # If it's not valid JSON, treat it as a regular string
                        answer = message + token
                if not answer and not reasoning_content:
                    # we didn't get an answer yet -> continue
                    continue

                if reasoning_content:
                    # we are thinking and using a deepseek model
                    thought = reasoning_content
                    message = answer or ""
                else:
                    if "<think>" in answer:
                        # Extract content after <think>
                        thought = answer.split("<think>")[1]
                        if "</think>" in thought:
                            # Extract content before </think> in thought
                            split = thought.split("</think>")
                            thought = split[0]
                            message = split[1] if len(split) > 1 else ""
                        else:
                            message = ""
                    elif "</think>" in answer:
                        # Extract content before </think> in thought
                        split = answer.split("</think>")
                        thought = split[0]
                        message = split[1] if len(split) > 1 else ""
                    else:
                        # No <think> or </think> present
                        thought = ""
                        message = answer or ""

                delta = ChoiceDelta(
                    content=message, thoughts=thought, instructions=instructions
                )
                if citations:
                    delta.citations = citations
                data_chunk = ChatCompletionsChunk(
                    id=chunk_id,
                    choices=[Choice(delta=delta, finish_reason="")],
                    created=datetime.now().isoformat(),
                )
                yield f"data: {data_chunk.model_dump_json()}\n\n"

            span.update_trace(output={"response": message})

        # Send stop with the final message
        # TODO: replace "message" with indipendent variable
        final_chunk = ChatCompletionsChunk(
            id=chunk_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(content=message, thoughts=thought),
                    finish_reason="stop",
                )
            ],
            created=datetime.now().isoformat(),
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
