import logging
import os
import sys
from pathlib import Path
from typing import Union

from fastapi.responses import StreamingResponse
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.globals import set_debug
from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableSerializable,
)
from langchain_core.vectorstores import VectorStore
from typing_extensions import Annotated, TypedDict

sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features, ResponseGenerationData
from bots.st.localization import get_localization
from bots.st.localization.base_local import BaseLocalization
from bots.study.helpers.helpers import get_llm
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
from framework.llm.base_llm import BaseLLM
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

VECTOR_STORE_DIRECTORY = "st"
STRUCTURE_ID = "st"
embeddings = LiteLLMEmbedding()
chain = RetrievalChain()


class StBuddy(BaseBot):
    """Bot for assisting in learning of software technology."""

    def __init__(self):
        """Initialize the stbuddy."""
        super().__init__(
            Topic.st_buddy.value,
            LocalizedString("ST Buddy", "ST Buddy"),
            LocalizedString(
                "Your Buddy for the Softwaretechnologie Lecture",
                "Dein Begleiter zur Vorlesung Softwaretechnologie",
            ),
            LocalizedString(
                "Your Buddy for the Softwaretechnologie Lecture"
                " - providing you with all kinds of information "
                "about the lecture, exercises, and organizational matters.",
                "Dein Begleiter zur Vorlesung Softwaretechnologie"
                " - versorgt dich mit allen Arten von Informationen "
                "über die Vorlesung, Übungen und Organisatorisches.",
            ),
            embeddings,
            features=[Features.TITLE, Features.STREAMING, Features.AIMODEL],
            color="#2969e8",
            priority=1,
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
        logger.info("StBuddy: Initializing chat")

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
        logger.info("StBuddy: Processing chat request")
        conversation_model = await open_conversation_base(request)

        if request.streaming:
            return StreamingResponse(self.stream_message(request, conversation_model))
        return await self.get_response(conversation_model)

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate the title for a chat/conversation."""
        logger.info("StBuddy: Generating title")
        messages = request.chat_history
        messages_for_prompt = messages[-2:] if len(messages) > 1 else messages
        locale = request.locale()
        prompt = get_localized_langfuse_prompt(
            "title", locale, request.response_preferences, chat=messages_for_prompt
        )
        llm_client = await get_llm(request.locale())
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
        logger.info("StBuddy: Preparing response")
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


st_buddy = StBuddy()
post = st_buddy.post


def load_module_db(module: str, locale: LocaleType) -> VectorStore:
    """Load the module database."""
    if not module:
        logger.info("StBuddy: Loading vector storage (all)")
        return FAISSVectorDB().load_local(
            str(Path(VECTOR_STORE_DIRECTORY).parent / "all"),
            embeddings,
        )

    logger.info("StBuddy: Loading vector storage")

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
    requested_llm: BaseLLM = None,
) -> RunnableSerializable:
    """Update the chain with the new information."""
    logger.info("StBuddy: Updating chain")

    if not requested_llm:
        requested_llm = await get_llm(locale)

    return chain.create_chain(
        requested_llm.llm(
            temperature=temperature, max_tokens=max_tokens, chat_id=chat_id
        ),
        prompt,
        session_id=chat_id,
        tags=["st-buddy"],
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
    requested_llm: BaseLLM = None,
) -> PromptTemplate:
    """Get the localized langfuse prompt."""
    if not requested_llm:
        # Default to llama-4 only for prompt retrieval, since no inference is done here
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

    if "st_role" in prompt.input_variables:
        role = requested_llm.get_langfuse_prompt(
            "st-description-" + locale.value.lower(),
            label=label,
            prompt_type="text",
        ).format()
        prompt = prompt.partial(st_role=role)

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
    logger.info("StBuddy: Setting up conversation")

    vector_db = await st_buddy.get_vector_store()  # TODO

    localized_llm: LiteLLM = await get_llm(request.locale(), request.llm_purpose)

    prompts = get_localized_langfuse_prompt(
        "st-open-conversation",
        locale,
        request.response_preferences,
        chat=messages,
        requested_llm=localized_llm,
    )

    context_docs = await multi_language_retriever(
        messages[-5:-1],
        last_message,
        vector_db,
        localized_llm=localized_llm,
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
        requested_llm=localized_llm,
    )

    sources = {i: Source.from_document(doc) for i, doc in enumerate(context_docs)}

    return ResponseGenerationData(
        chain_config=chain_config,
        created_chain=created_chain,
        sources=sources,
        llm_model=localized_llm.get_model_name(),
    )


class ModuleMultiQueries(TypedDict):
    """A typed dictionary for the multi-language retriever and the module detection."""

    module: Annotated[
        str,
        ...,
        "The detected module name, either 'content', 'exercises', or 'organizational'",
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
        "st-module-retriever-query",
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
            "langfuse_tags": ["st-buddy", "multi-retriever"],
        },
    )

    module_queries = await created_chain.ainvoke({"last_message": message})

    # Get queries from the response or fall back to original message
    queries = []
    detected_module = None
    if isinstance(module_queries, dict):
        queries_dict = module_queries.get("queries", {})
        queries = queries_dict.get("german", []) + queries_dict.get("english", [])

    db = await st_buddy.get_db()
    topic = await db.get_topic_by_code(STRUCTURE_ID)
    # Extract the detected module if available
    if isinstance(module_queries, dict) and "module" in module_queries:
        detected_module = module_queries["module"]
        logger.info(f"StBuddy: Detected module from queries: {detected_module}")

        if detected_module.lower() in ["content", "exercises", "organizational"]:
            competence = await db.get_competence_by_code(
                f"st_{detected_module.lower()}"
            )  # TODO: is this right?

    docs = []
    if detected_module != "organizational":
        for query in queries:
            docs.extend(
                doc[0]
                for doc in vector_db.similarity_search_with_relevance_scores(
                    query,
                    k=3,
                    score_threshold=0.2,
                    competence_id=competence.idcompetence if competence else None,
                    topic_id=topic.idtopic if topic else None,
                )
            )

    if not docs:
        logger.info("StBuddy: No documents found. Trying again without threshold.")
        for query in queries:
            docs.extend(
                vector_db.similarity_search(
                    query,
                    k=3,
                    competence_id=competence.idcompetence if competence else None,
                    topic_id=topic.idtopic if topic else None,
                )
            )

    # TODO: Excercises should again be returned as a whole
    # and not only the current chunk -> Change needed in DB

    # Remove duplicates
    unique_contents = {}
    for doc in docs:
        key = doc.page_content
        unique_contents[key] = doc
    new_docs = list(unique_contents.values())
    return new_docs
