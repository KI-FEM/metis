import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableSerializable
from langfuse import Langfuse
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))
from framework.api_types.choice import ChatCompletionsChunk, Choice, ChoiceDelta
from framework.api_types.learning_type import LearningTypeModel
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.module import Module, Skill
from framework.api_types.request_format import Message, RequestModel, Sender
from framework.api_types.response_format import Response, Source, TitleResponse
from framework.chains.base_chain import BaseChain
from framework.chains.passthrough_chain import PassthroughChain
from framework.config import KEEP_LAST_MESSAGES_UNTIL, MAX_MESSAGES_BEFORE_SUMMARIZATION
from framework.llm.base_llm import BaseLLM
from framework.llm.lite_llm import LiteLLM

logger = logging.getLogger()


class SummaryResult(BaseModel):
    """Result of the summarization."""

    messages: list[Message]
    includes_summary: bool
    summary: Optional[str]


class ResponseGenerationData(BaseModel):
    """Model for transporting data for generating chat responses."""

    chain_config: dict
    created_chain: RunnableSerializable
    sources: dict[int, Source]
    llm_model: str


class Features(Enum):
    """Features of the bot."""

    TITLE = "title" # Generate a title for the conversation
    INSPIRATIONS = "inspirations" # Generate inspiration messages for the user
    INITIATIVE = "initiative" # Give over initiative to the bot
    QUIZ = "quiz" # Generate quiz to test the user's knowledge
    FEEDBACK = "feedback" # Provide feedback on the bot's performance
    PLAN = "plan" # Plan the next session
    STREAMING = "streaming" # Enable streaming responses
    SUMMARY = "summary" # Generate automatic summaries if the conversation is long
    AIMODEL = "aimodel" # Let the user select the AI model to use for the conversation


class BaseBot(ABC):
    """A chat bot that can be used to chat with the user."""

    DISABLE_STREAMING = True
    router: APIRouter

    def __init__(
        self,
        identifier: str,
        name: LocalizedString,
        short_description: LocalizedString,
        long_description: LocalizedString,
        chain: BaseChain,
        llm_client: BaseLLM,
        skill_topic: bool = False,
        features: List[Features] = None,
        priority: int = 0,
        enabled: bool = True,
        color: str = "#000000",
    ) -> None:
        """Initialize the chat bot."""
        self.chain = chain
        self.id = identifier
        self.name = name
        self.short_description = short_description
        self.long_description = long_description
        self.llm_client = llm_client
        self.skill_topic = skill_topic
        self._routes = {}
        self.router = APIRouter(prefix=f"/topic/{self.id}")
        self.features = features if features is not None else []
        self._decorated_functions = {}
        self.priority = priority
        self.enabled = enabled
        self.color = color

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

    @abstractmethod
    def get_modules(self) -> List[Union[Module, Skill]]:
        """Get the modules of the bot."""

    @abstractmethod
    async def init_chat(self, request: RequestModel) -> Response:
        """Initialize the chat with the bot."""

    @abstractmethod
    async def chat_invoke(self, request: RequestModel) -> Response:
        """Chat with the bot."""

    async def chat_stream(self, request: RequestModel) -> StreamingResponse:
        """Chat with the bot through streaming."""
        if not self.features or Features.STREAMING not in self.features:
            raise NotImplementedError("Streaming feature not implemented.")

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate a title for the given conversation."""
        if not self.features or Features.TITLE not in self.features:
            raise NotImplementedError("Title feature not implemented.")

    async def summarize(self, request: RequestModel) -> Response:
        """Summarize the chat history asynchronously.

        This method is called by the frontend during idle periods to summarize long
        conversations without blocking the main chat interaction.
        """
        if not self.features or Features.SUMMARY not in self.features:
            raise NotImplementedError("Summary feature not implemented.")

    def _pretty_name(self, name):
        return name.replace("_", " ")

    async def invoke(self, chain_info: dict) -> Response:
        """Invoke the chain with the given information."""
        return await self.chain.get_chain().ainvoke(chain_info)

    def get_learning_type_description(
        self, langfuse: Langfuse, learning_type: LearningTypeModel, locale: LocaleType
    ) -> str:
        """Get the description of the learning type."""
        return langfuse.get_prompt(
            f"learning_type_description-{learning_type.id.value.lower()}-{locale.value.lower()}",
            label="latest",
            type="text",
        ).get_langchain_prompt()

    async def summarize_chat(
        self, request: RequestModel, default_llm: LiteLLM = None
    ) -> SummaryResult:
        """Summarize the chat."""
        includes_summary = False
        messages = request.chat_history
        messages_since_last_summary = messages
        previous_summary = None

        # go through the messages last max_messages and find the last summary
        for i in range(
            max(len(messages) - MAX_MESSAGES_BEFORE_SUMMARIZATION, 0), len(messages)
        ):
            if hasattr(messages[i], "summary") and messages[i].summary:
                # if the message has a summary, add it to the
                # messages_since_last_summary plus the following messages
                # and break the loop
                messages_since_last_summary = [
                    Message(message=messages[i].summary, sender="assistant")
                ] + messages[i + 1 :]
                includes_summary = True
                previous_summary = messages[i].summary
                break

        # if the number of messages since the last summary is greater than
        # the max_messages_to_keep, trim the messages by summarizing the last
        # max_messages_to_keep messages
        if len(messages_since_last_summary) > MAX_MESSAGES_BEFORE_SUMMARIZATION:
            trimmed_messages = messages_since_last_summary[:-KEEP_LAST_MESSAGES_UNTIL]

            localized_llm = default_llm
            if request.llm:
                localized_llm = LiteLLM(model_name=request.llm.label)

            label = (
                "latest"
                if os.getenv("ENVIRONMENT", "development") == "development"
                else "production"
            )
            summarization_prompt = localized_llm.get_langfuse_prompt(
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
                localized_llm.llm(), summarization_prompt
            )
            summary = await chain.ainvoke(
                {
                    "previous_summary": summary_text + previous_summary
                    if previous_summary
                    else ""
                }
            )
            return SummaryResult(
                messages=[Message(message=summary, sender="assistant")]
                + messages_since_last_summary[-KEEP_LAST_MESSAGES_UNTIL:],
                includes_summary=True,
                summary=summary,
            )
        else:
            return SummaryResult(
                messages=messages_since_last_summary,
                includes_summary=includes_summary,
                summary=None,
            )

    async def stream_message(
        self, 
        request: RequestModel, 
        data: Union[ResponseGenerationData, Response], 
        structured: bool = False # TODO: this is temporary
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
            structured (bool): Whether the response is structured or not. Defaults to
                False.

        Returns:
            Async generator yielding message chunks as strings.

        """
        if isinstance(data, Response):
            # if we got a response that we should send through the stream,
            # simply send the full message
            for message in data.messages:
                # Create a delta for each message
                delta = ChoiceDelta()
                if message.thoughts:
                    delta.thoughts = message.thoughts
                if message.message:
                    delta.content = message.message
                if message.meta_information:
                    if message.meta_information.llm_model:
                        delta.llm_model = message.meta_information.llm_model
                    if message.meta_information.sources:
                        delta.sources = message.meta_information.sources
                if message.buttons:
                    delta.buttons = message.buttons
                if message.sender:
                    delta.sender = message.sender

                data_chunk = ChatCompletionsChunk(
                    id=request.find_store("chat_id", ""),
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
                id=request.find_store("chat_id", ""),
                choices=[Choice(finish_reason="stop")],
                created=datetime.now().isoformat(),
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            return

        data: ResponseGenerationData = data
        created_chain: RunnableSerializable = data.created_chain
        chain_config = data.chain_config

        # Send initial metadata
        first_chunk = ChatCompletionsChunk(
            id=request.find_store("chat_id", ""),
            choices=[
                Choice(
                    delta=ChoiceDelta(
                        sender=Sender.ASSISTANT.value,
                        sources=data.sources,
                        llm_model=data.llm_model,
                    ),
                    finish_reason="",
                )
            ],
            created=datetime.now().isoformat(),
        )
        yield f"data: {first_chunk.model_dump_json()}\n\n"

        # Stream message content
        token_stream_iterator = created_chain.astream(chain_config)
        thinking = False  # track whether we are in a <think> block
        message = ""  # build message content
        previous_token = ""  # store the previous token

        async for token in token_stream_iterator:
            answer = None
            citations = None
            if isinstance(token, dict):
                if "answer" in token:
                    answer = token["answer"] or ""
                if "citations" in token:
                    citations = token["citations"] or []
            elif isinstance(token, str):
                answer = token
            thought = None
            if not answer:
                # we didn't get an answer yet -> continue
                continue
            if structured and previous_token in answer:
                temp_answer = answer
                answer = answer.replace(previous_token, "")
                previous_token = temp_answer
            if "<think>" in answer:
                # we are in a <think> block -> set the thought to the block's content
                thinking = True
                thought = answer.split("<think>")[1]
            if "</think>" in answer:
                # end of a <think> block -> set the thought to the block's content
                thought = answer.split("</think>")[0]
                if "<think>" in thought:  # both <think> and </think> are in the token
                    thought = thought.split("<think>")[1]

            if not thinking:
                message += answer
            delta = ChoiceDelta(
                content=answer,
            )
            if thinking:
                delta = ChoiceDelta(thoughts=thought)
            if citations:
                delta.citations = citations
            if thought is not None and not thinking:
                # didnt get a <think> but got a </think>
                split = answer.split("</think>")
                delta = ChoiceDelta(
                    content=split[1] if len(split) > 1 else "",
                    thoughts=message,
                    instructions=["discard"],
                )
                message=split[1] if len(split) > 1 else ""
            data_chunk = ChatCompletionsChunk(
                id=request.find_store("chat_id"),
                choices=[Choice(delta=delta, finish_reason="")],
                created=datetime.now().isoformat(),
            )
            if "</think>" in answer:
                thinking = False
            yield f"data: {data_chunk.model_dump_json()}\n\n"

        # Send stop with the final message
        #TODO: replace "message" with indipendent variable
        final_chunk = ChatCompletionsChunk(
            id=request.find_store("chat_id"),
            choices=[Choice(delta=ChoiceDelta(content=message), 
                            finish_reason="stop")],
            created=datetime.now().isoformat(),
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
