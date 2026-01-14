import json
import logging
import os
import sys
from pathlib import Path

from fastapi.responses import StreamingResponse
from langchain_core.globals import set_debug

sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features, Module, ResponseGenerationData
from bots.study.helpers.helpers import get_llm
from bots.study.helpers.models import InspirationsResponse
from framework.api_types.localized_string import LocalizedString
from framework.api_types.request_format import Message, RequestModel
from framework.api_types.response_format import (
    MetaInformation,
    Response,
    SummaryResponse,
    TitleResponse,
)
from framework.api_types.response_preferences import (
    fill_response_preferences,
)
from framework.api_types.topics import Topic
from framework.chains.passthrough_chain import PassthroughChain
from framework.config import get_config

dev = os.environ.get("ENVIRONMENT", "development") == "development"
set_debug(dev)

# Configure logging format to include timestamp, class and method
logging.basicConfig(
    format="%(asctime)s [%(name)s] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger()
chain = PassthroughChain()

class PassthroughBot(BaseBot):
    """A chat bot that can be used to chat with the user."""

    def __init__(
        self,
        identifier=Topic.passthrough_bot.value,
        name=LocalizedString("Free Chat", "Freier Chat"),
        description=LocalizedString(
            "Chat freely with our AI.", "Chatte offen mit unserer KI."
        ),
        long_description=LocalizedString(
            "Chat freely with our AI. You can ask any question you like.",
            "Chatte offen mit unserer KI. Du kannst jede Frage stellen, "
            "die du möchtest.",
        ),
    ) -> None:
        """Initialize the chat bot."""
        super().__init__(
            identifier,
            name,
            description,
            long_description,
            None,  # No embeddings needed for passthrough
            features=[
                Features.TITLE,
                Features.INSPIRATIONS,
                Features.STREAMING,
                Features.SUMMARY,
                Features.AIMODEL,
            ],
            color="#ea964d",
            priority=5,
            optional=False,
        )

        # Cache for inspirations
        self._inspirations_cache = None
        self._load_inspirations()

    def _load_inspirations(self):
        """Load inspirations from JSON file and cache them."""
        # Define fallback inspirations
        fallback_inspirations = [
            LocalizedString(
                "Give me a recipe for your tastiest cookies",
                "Gib mir ein Rezept für deine leckersten Kekse",
            ),
            LocalizedString(
                "Recommend a fantasy book.", "Empfehle mir ein Fantasy-Buch."
            ),
            LocalizedString(
                "What's the best way to learn a new language?",
                "Wie lerne ich am besten eine neue Sprache?",
            ),
        ]

        json_path = Path(__file__).parent / "inspirations.json"
        try:
            with json_path.open("r") as f:
                data = json.load(f)
                suggestions = data.get("suggestions", [])

            # Convert each suggestion to a LocalizedString
            inspirations = []
            for suggestion in suggestions:
                en = suggestion.get("en", "")
                de = suggestion.get("de", "")
                inspirations.append(LocalizedString(en, de))

            self._inspirations_cache = inspirations
            logger.info("Loaded %s inspirations from file", len(inspirations))
        except Exception as e:
            logger.error("Error loading inspirations: %s. Using fallback", e)
            # Use fallback inspirations if file loading fails
            self._inspirations_cache = fallback_inspirations

    def get_modules(self) -> list[Module]:
        """Return empty list for modules."""
        return []

    async def init_chat(self, request: RequestModel) -> Response | StreamingResponse:
        """Start the chat."""
        logger.info("PassthroughBot: Initializing chat")
        resp = Response.from_message("Welcome! You can freely chat with me here.")
        resp.messages[0].meta_information = MetaInformation(source="init_chat")
        return resp

    async def chat_invoke(self, request: RequestModel) -> Response | StreamingResponse:
        """Invoke the passthrough bot."""
        logger.info("PassthroughBot: Processing chat request")
        messages = request.chat_history
        chat_id = request.find_store("chat_id")

        llm = None
        # Check if the user has selected a specific LLM
        llm = await get_llm(request.locale(), request.llm_purpose)

        # Walk through the messages in reverse order to find the last summary
        conversation_history = []
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            if hasattr(message, "summary") and message.summary:
                # Found a summary - take all messages from this point forward
                conversation_history = [
                    Message(
                        content=message.summary,
                        type="assistant",
                        timestamp=message.timestamp,
                    )
                ] + messages[i + 1 :]
                break

        # If no summary was found, use all messages
        if not conversation_history:
            conversation_history = messages

        prompt = llm.get_langfuse_prompt("passthrough", chat=conversation_history)
        prompt = fill_response_preferences(
            prompt, request.response_preferences, request.locale()
        )

        # create the chain
        created_chain = chain.create_chain(
            llm.llm_chatopenai(chat_id=chat_id),
            prompt,
            session_id=chat_id,
            tags=[self.id],
            use_dict_output_parser=True,
        )
        if request.streaming:
            # streaming response
            data = ResponseGenerationData(
                chain_config={},
                created_chain=created_chain,
                sources={},
                llm_model=llm.get_model_name(),
            )
            return StreamingResponse(
                self.stream_message(request, data), media_type="text/event-stream"
            )

        # non-streaming response
        response_dict = await created_chain.ainvoke({})
        message_response = await self.parse_response_content(response_dict)
        message_response.meta_information = MetaInformation(
            llm_model=llm.get_model_name()
        )

        # return the response
        return Response(messages=[message_response])

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate the title for a chat/conversation."""
        logger.info("PassthroughBot: Generating title")
        messages = request.chat_history
        messages_for_prompt = messages[-2:] if len(messages) > 1 else messages
        chat_id = request.find_store("chat_id")

        llm_client = await get_llm(request.locale())
        title_response = (
            await PassthroughChain()
            .create_chain(
                llm_client.llm(max_tokens=200, chat_id=chat_id),
                llm_client.get_langfuse_prompt("title-en", chat=messages_for_prompt),
                session_id=chat_id,
                tags=["title"],
            )
            .ainvoke({})
        )

        return TitleResponse(title=title_response)

    async def inspirations(self, request):
        """Return some inspiration for the user."""
        locale = request.locale()
        logger.info("PassthroughBot: Providing inspirations")

        # Use cached inspirations
        if self._inspirations_cache is None:
            # Reload if cache is empty for some reason
            self._load_inspirations()

        response = InspirationsResponse(
            messages=[inspo.get(locale) for inspo in self._inspirations_cache]
        )
        return response

    async def summarize(self, request: RequestModel) -> SummaryResponse:
        """Summarize the chat history.

        This endpoint is called asynchronously by the frontend to summarize long
        conversations without blocking the main chat interaction.
        """
        logger.info("PassthroughBot: Summarizing chat")
        llm_client = await get_llm(request.locale())
        summary_result = await self.summarize_chat(request, llm_client=llm_client)
        keep_last_msgs_until = await get_config("KEEP_LAST_MESSAGES_UNTIL")
        if summary_result.summary:
            return SummaryResponse(
                summary=summary_result.summary,
                keep_last_messages_until=int(keep_last_msgs_until),
            )
        return SummaryResponse(summary="", keep_last_messages_until=0)


passthrough_bot = PassthroughBot()
post = passthrough_bot.post
