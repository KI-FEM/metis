import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Union

from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from langchain_core.globals import set_debug
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableSerializable,
)
from langchain_core.vectorstores import VectorStore
from typing_extensions import Annotated, TypedDict

from bots.study.helpers.helpers import get_llm

sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features, ResponseGenerationData
from bots.dissy.localization import get_localization
from bots.dissy.localization.base_local import BaseLocalization
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.module import Module
from framework.api_types.request_format import Message, MessageType, RequestModel
from framework.api_types.response_format import (
    MessageResponse,
    MetaInformation,
    Response,
    Source,
    TitleResponse,
)
from framework.api_types.response_preferences import (
    ResponsePreferences,
    fill_response_preferences,
)
from framework.api_types.topics import Topic
from framework.chains import PassthroughChain, RetrievalChain
from framework.chains.base_chain import BaseChain
from framework.llm.lite_llm import LiteLLM
from framework.rag.embeddings.lite_llm_embedding import LiteLLMEmbedding
from framework.rag.vector_dbs.faiss import FAISSVectorDB

logger = logging.getLogger()
dev = os.environ.get("ENVIRONMENT", "development") == "development"
set_debug(dev)

# Configure logging format to include timestamp, class and method
logging.basicConfig(
    format="%(asctime)s [%(name)s] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

VECTOR_STORE_DIRECTORY = "ds"
STRUCTURE_ID = "ds"
embeddings = LiteLLMEmbedding()
chain = RetrievalChain()


class Dissy(BaseBot):
    """Bot for assisting in learning of Secrets behind LLMs."""

    def __init__(self):
        """Initialize Dissy."""
        super().__init__(
            Topic.dissy.value,
            LocalizedString("Dissy", "Dissy"),
            LocalizedString(
                "Your Buddy for the Lecture Distributed Systems.",
                (
                    "Dein Begleiter für die Vorlesung Distributed Systems."
                ),
            ),
            LocalizedString(
                "Your Buddy for the lecture Distributed Systems"
                " - providing you with all kinds of information "
                "about the lecture, exercises, and organizational matters.",
                "Dein Begleiter zur Vorlesung Distributed Systems"
                " - versorgt dich mit allen Arten von Informationen "
                "über die Vorlesung, Übungen und Organisatorisches.",
            ),
            embeddings,
            features=[Features.TITLE, Features.STREAMING, Features.AIMODEL],
            color="#2969e8",
            avatar="/static/images/{theme}/dissy.png",
            tag="INF",
        )

    async def get_modules(self) -> list[Module]:
        """Get the available modules."""
        db = await self.get_db()
        topic = await db.get_topic_by_code(STRUCTURE_ID)
        return await db.get_modules(topic.idtopic)

    async def init_chat(self, request: RequestModel) -> Response:
        """Start chat and send greeting message."""
        locale = request.locale()
        logger.info("Dissy: Initializing chat")

        return Response(
            messages=[
                MessageResponse(
                    content=localized(locale, "greeting_message"),
                    meta_information=MetaInformation(source="init_chat"),
                )
            ]
        )

    async def chat_invoke(self, request: RequestModel) -> Response | StreamingResponse:
        """Invoke the study competence bot."""
        logger.info("Dissy: Processing chat request")
        conversation_model = await open_conversation_base(request)

        if request.streaming:
            return StreamingResponse(self.stream_message(request, conversation_model))
        return await self.get_response(conversation_model)

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate the title for a chat/conversation."""
        logger.info("Dissy: Generating title")
        messages = request.chat_history
        messages_for_prompt = messages[-2:] if len(messages) > 1 else messages
        locale = request.locale()
        prompt = get_localized_langfuse_prompt(
            "title", locale, request.response_preferences, chat=messages_for_prompt
        )
        llm_client = await get_llm(locale)
        title_response = (
            await PassthroughChain()
            .create_chain(
                llm_client.llm(
                    max_tokens=200, chat_id=request.find_store("chat_id")
                ),
                prompt,
            )
            .ainvoke({})
        )

        return TitleResponse(title=title_response)

    async def get_response(
        self, conversation_model: Union[ResponseGenerationData, Response]
    ) -> Response:
        """Get the response without streaming."""
        logger.info("Dissy: Preparing response")
        if isinstance(conversation_model, Response):
            return conversation_model

        # If conversation_model is not of instance Response,
        # we assume it's a OpenConversationModel
        conversation_model: ResponseGenerationData = conversation_model

        response = await conversation_model.created_chain.ainvoke(
            conversation_model.chain_config
        )

        message_response = await self.parse_response_content(response)
        message_response.meta_information = MetaInformation(
            sources=conversation_model.sources,
            llm_model=conversation_model.llm_model,
        )
        return Response(messages=[message_response])


dissy = Dissy()
post = dissy.post


def load_module_db(module: str, locale: LocaleType) -> VectorStore:
    """Load the module database."""
    if not module:
        logger.info("Dissy: Loading vector storage (all)")
        return FAISSVectorDB().load_local(
            str(Path(VECTOR_STORE_DIRECTORY).parent / "all"),
            embeddings,
        )

    logger.info("Dissy: Loading vector storage")

    # TODO: currently all content is stored in the german folder
    # therefore, the locale.value gets ignored and only german is used
    return FAISSVectorDB().load_local(
        str(Path(VECTOR_STORE_DIRECTORY) / "de" / module),
        embeddings,
    )


async def update_chain(
    prompt: PromptTemplate,
    locale: LocaleType,
    temperature: float = 0.7,
    max_tokens: int = None,
    chat_id: str = None,
    requested_llm: LiteLLM = None,
) -> RunnableSerializable:
    """Update the chain with the new information."""
    logger.info("Dissy: Updating chain")
    if requested_llm is None:
        requested_llm = await get_llm(locale)

    return chain.create_chain(
        requested_llm.llm(
            temperature=temperature, max_tokens=max_tokens, chat_id=chat_id
        ),
        prompt,
        session_id=chat_id,
        tags=["dissy"],
    )


def localized(locale: LocaleType, key: str) -> str:
    """Localize the bot."""
    localization: BaseLocalization = get_localization(locale)
    return localization.get(key, f"Failed to localize {key}.")


def get_localized_langfuse_prompt(
    base_name: str,
    locale: LocaleType,
    response_preferences: ResponsePreferences = None,
    chat: list[Message] = None,
    requested_llm: LiteLLM = None,
) -> PromptTemplate:
    """Get the localized langfuse prompt."""
    if requested_llm is None:
        # some default model just to get the prompt, no inference required
        requested_llm = LiteLLM(model_name="llama-4")

    environment = os.getenv("ENVIRONMENT", "development")
    label = "production" if environment == "production" else "latest"
    prompt: PromptTemplate = requested_llm.get_langfuse_prompt(
        base_name + "-" + locale.value.lower(),
        chat=chat,
        prompt_type="chat",
        label=label,
    )
    metadata = prompt.metadata

# TODO: create prompts and rename them
    if "dissy_role" in prompt.input_variables:
        role = requested_llm.get_langfuse_prompt(
            "dissy-description-" + locale.value.lower(),
            label=label,
            prompt_type="text",
        ).format()
        prompt = prompt.partial(dissy_role=role)

    prompt = fill_response_preferences(prompt, response_preferences, locale)

    prompt.metadata = metadata
    return prompt


async def open_conversation_base(
    request: RequestModel,
) -> Union[ResponseGenerationData, Response]:
    """Prerequisites for the open conversation functions."""
    locale = request.locale()

    messages = request.chat_history
    last_message = next(
        (msg.content for msg in reversed(messages) if msg.type == MessageType.USER),
        "No user message found",
    )
    selected_module = request.find_store("selected_competence", None)
    requested_llm = await get_llm(locale, request.llm_purpose)

    logger.info("Dissy: Setting up conversation")

    vector_db = await dissy.get_vector_store()  # TODO

    prompts = get_localized_langfuse_prompt(
        "dissy-open-conversation",
        locale,
        request.response_preferences,
        chat=messages,
        requested_llm=requested_llm,
    )

    context_docs = await multi_language_retriever(
        messages[-5:-1],
        last_message,
        vector_db,
        localized_llm=requested_llm,
        locale=locale,
        chat_id=request.find_store("chat_id"),
    )

    chain_config = {
        "context": context_docs,
        "module": selected_module or "",
    }

    created_chain = await update_chain(
        prompts,
        locale,
        chat_id=request.find_store("chat_id"),
        requested_llm=requested_llm,
    )

    sources = {i: Source.from_document(doc) for i, doc in enumerate(context_docs)}

    return ResponseGenerationData(
        chain_config=chain_config,
        created_chain=created_chain,
        sources=sources,
        llm_model=requested_llm.get_model_name(),
    )


class Modules(Enum):
    """Enumeration for the different modules."""

    CONTENT = "content"
    EXERCISES = "exercises"
    ORGANIZATIONAL = "organizational"


class ModuleMultiQueries(TypedDict):
    """A typed dictionary for the multi-language retriever and the module detection."""

    module: Annotated[
        Modules,
        ...,
        (
            "The detected module name, either 'content' (anything "
            "relating to the lecture content), 'exercises' (anything "
            "relating to the exercises), or 'organizational' (relating "
            "to organizational matters)"
        ),
    ]
    queries: Annotated[
        dict[str, list[str]],
        ...,
        "Dictionary with sub-lists of German and English queries",
    ]


async def multi_language_retriever(
    messages: list[Message],
    message: str,
    vector_db: VectorStore,
    locale: LocaleType,
    localized_llm: LiteLLM,
    chat_id: str = None,
) -> list[Document]:
    """Retrieves relevant documents from a vector database based on a user message.

    Args:
        messages (list[Message]): The chat history messages to provide context.
        message (str): user message
        vector_db (VectorStore): vector database
        locale (LocaleType): The locale for localization.
        localized_llm (LiteLLM): The localized LLM for processing the query.
        chat_id (str, optional): optional identifier for tracing and logging.

    Returns:
        list[Document]: A list of unique documents relevant to the user's message.

    """
    prompt = get_localized_langfuse_prompt(
        "dissy-module-retriever-query",
        locale,
        chat=messages,
    )

    created_chain = (
        RunnablePassthrough().assign()
        | prompt
        | localized_llm.llm_chatopenai(chat_id=chat_id).with_structured_output(
            ModuleMultiQueries
        )
    ).with_config(
        callbacks=[BaseChain.get_langfuse_callback()],
        metadata={
            "langfuse_session_id": chat_id,
            "langfuse_tags": ["dissy", "multi-retriever"],  # TODO
        },
    )

    module_queries: ModuleMultiQueries = await created_chain.ainvoke(
        {"last_message": message}
    )

    # Get queries from the response or fall back to original message
    queries = []
    detected_module = None
    if isinstance(module_queries, dict):
        queries_dict = module_queries.get("queries", {})

        # put all queries into a list
        for lang_queries in queries_dict.values():
            queries.extend(lang_queries)

    db = await dissy.get_db()
    topic = await db.get_topic_by_code(STRUCTURE_ID)
    # Extract the detected module if available
    if isinstance(module_queries, dict) and "module" in module_queries:
        detected_module = module_queries.get("module", None)
        logger.info(f"Dissy: Detected module from queries: {detected_module}")

        competence = await db.get_competence_by_code(f"btsllm_{detected_module}")

    docs = {}
    if detected_module != "organizational":
        # we only search with threshold for content and exercises
        for query in queries:
            for doc in vector_db.similarity_search_with_relevance_scores(
                query,
                k=3,
                score_threshold=0.2,
                competence_id=competence.idcompetence if competence else None,
                topic_id=topic.idtopic if topic else None,
            ):
                docs[doc[0].id] = doc[0]

    if not docs:
        # we search for organizational or no documents found without threshold
        logger.info("Dissy: No documents found. Trying again without threshold.")
        for query in queries:
            for doc in vector_db.similarity_search(
                query,
                k=3,
                competence_id=competence.idcompetence if competence else None,
                topic_id=topic.idtopic if topic else None,
            ):
                docs[doc.id] = doc

    # TODO: Excercises should again be returned as a whole
    # and not only the current chunk -> Change needed in DB

    # Remove duplicates
    new_docs = list(docs.values())
    return new_docs
