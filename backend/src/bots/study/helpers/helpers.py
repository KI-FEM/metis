import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Literal, Union

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, ValidationError

sys.path.append(str(Path(__file__).parent.parent.parent))

from bots.study.localization import get_localization
from bots.study.localization.base_local import BaseLocalization
from framework.api_types.ai_models import (
    LLM,
    LLMPurpose,
    PurposeConfigModel,
    PurposeListConfigModel,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import (
    LearnerModel,
    Message,
    RequestModel,
    ResponsePreferences,
)
from framework.api_types.response_format import Source
from framework.api_types.response_preferences import (
    fill_response_preferences,
)
from framework.config import get_all_purposes_with_translation, get_purpose
from framework.db.database import Database
from framework.db.db_types import LearningUnitCombined
from framework.llm.base_llm import BaseLLM
from framework.llm.lite_llm import LiteLLM
from framework.llm.multilingual_llm import MultiLingualLLM
from framework.rag.embeddings.lite_llm_embedding import LiteLLMEmbedding
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever

logger = logging.getLogger(__name__)

TOPIC_CODE = "study_competence"
embeddings = LiteLLMEmbedding()
llm_client = MultiLingualLLM()


async def get_ai_models() -> PurposeListConfigModel:
    """Get the AI models from the configuration."""
    try:
        models = await get_all_purposes_with_translation()
        
        return PurposeListConfigModel(
            purposes=[
                PurposeConfigModel(
                    id=purpose.code,
                    label=purpose.name,
                    description=purpose.description,
                    icon=purpose.icon,
                    models=purpose.models,
                )
                for purpose in models if purpose.icon
            ]
        )
    except ValidationError as e:
        logger.error(f"Error validating AI models: {e}")
        return None


async def get_llms_for_purpose(selected_purpose: LLMPurpose) -> list[LLM]:
    """Selects the best available LLM for the given purpose and locale.

    Args:
        selected_purpose: The purpose of the LLM (e.g., 'optimal')
        locale: Optional locale preference

    Returns:
        The best LLM for the given purpose and locale, or None if no suitable LLM.

    """
    purpose = await get_purpose(selected_purpose.value)

    if not purpose:
        return []

    return [
        LLM(
            id=model_id,
            model_name=model_id,
            label=model_id,
            status="healthy",
        )
        for model_id in purpose.models
    ]


async def init_llm_client():
    """Initialize the multilingual LLM client with default models.

    Has to be called async to await the default model names from the db config.
    """
    llm_client.add_llm(
        LocaleType.EN, LiteLLM(model_name=await LiteLLM.get_default_model())
    )
    llm_client.add_llm(
        LocaleType.DE,
        LiteLLM(model_name=await LiteLLM.get_default_model(LLMPurpose.GERMAN)),
    )


async def get_llm(
    locale: LocaleType, requested_purpose: LLMPurpose = LLMPurpose.OPTIMAL
) -> LiteLLM:
    """Get the LLM for the given locale and requested purpose.

    Defaults to the purpose 'optimal' if none is provided.
    """
    if requested_purpose is None:
        requested_purpose = LLMPurpose.OPTIMAL
    localized_llm: LiteLLM = llm_client.get_llm(locale)
    if not localized_llm:  # llm_client not initialized yet
        await init_llm_client()
        localized_llm = llm_client.get_llm(locale)

    llms = await get_llms_for_purpose(requested_purpose)
    if llms:
        localized_llm: LiteLLM = LiteLLM(
            model_name=llms[0].model_name,
            fallback_models=[llm.model_name for llm in llms[1:]]
            if len(llms) > 1
            else None,
        )

    return localized_llm


def localized(locale: str, key: str) -> str:
    """Get the localized string for the given key depending on given locale."""
    localization: BaseLocalization = get_localization(locale)
    return localization.get(key, f"Failed to localize {key}.")


def get_localized_langfuse_prompt(
    base_name: str,
    locale: LocaleType,
    response_preferences: Union[ResponsePreferences, None] = None,
    chat: list[Message] = None,
    requested_llm: BaseLLM = None,
    prompt_type: str = "chat",
    label_override: str = None,
) -> PromptTemplate:
    """Get the langfuse prompt for the given name based on the provided locale.

    This function retrieves the prompt template for the specified base name and locale,
    and fills in any necessary variables based on the provided learning type and chat
    history. It also handles the competence role and learning type description if
    applicable.

    Args:
        base_name (str): The base name of the prompt.
        locale (LocaleType): The locale for localization.
        response_preferences (ResponsePreferences): The response preferences of the user
        chat (list[Message], optional): The chat history. Defaults to None.
        requested_llm (LLM, optional): The requested LLM. Defaults to None.
        prompt_type (str, optional): The type of prompt to retrieve. Defaults to "chat".
        label_override (str, optional): The label to use for fetching. Defaults to None.

    Returns:
        PromptTemplate: The filled prompt template.

    """
    # set LLM
    if not requested_llm:
        # some default model just to get the prompt, no inference required
        requested_llm = LiteLLM(model_name="llama-4")
    environment = os.getenv("ENVIRONMENT", "development")
    langfuse_label = (
        label_override or os.getenv("LANGFUSE_LABEL", "production")
        if environment == "production"
        else "latest"
    )

    # get the prompt template
    # use the tag "latest" development and "production" or LANGFUSE_LABEL for production
    prompt: PromptTemplate = requested_llm.get_langfuse_prompt(
        base_name + "-" + locale.value.lower(),
        chat=chat,
        prompt_type=prompt_type,
        label=langfuse_label,
    )
    metadata = prompt.metadata

    # if the prompt contains the competence role, fill it in
    if "competence_role" in prompt.input_variables:
        competence_role = requested_llm.get_langfuse_prompt(
            "competence-description-" + locale.value.lower(),
            prompt_type="text",
        ).format()
        prompt = prompt.partial(competence_role=competence_role)

    if "current_date" in prompt.input_variables:
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        prompt = prompt.partial(current_date=current_date)

    if response_preferences is not None:
        # if the prompt contains response preferences, fill them in from the preferences
        prompt = fill_response_preferences(prompt, response_preferences, locale)

    prompt.metadata = metadata
    return prompt


def get_tool_descriptions_from_langfuse(
    locale: LocaleType,
    tools: list = None,
    label_override: str = None,
) -> tuple[str, str]:
    """Get the tool descriptions from Langfuse for the given tools and locale.

    This function retrieves the tool descriptions for the specified tools and locale
    from the Langfuse API.

    Args:
        locale (LocaleType): The locale for localization.
        tools (list): The list of tool names. Defaults to [].
        label_override (str, optional): The label to use for fetching. Defaults to None.

    Returns:
        tuple[str, str]: A tuple containing the tool list and tool descriptions.

    """
    if not tools:
        return "No tools available.", ""
    environment = os.getenv("ENVIRONMENT", "development")
    langfuse_label = (
        label_override or os.getenv("LANGFUSE_LABEL", "production")
        if environment == "production"
        else "latest"
    )
    tool_descriptions = []
    # Fetch descriptions from Langfuse
    for tool in tools:
        # Skip the "think" tool - description in main sys prompt
        if tool == "think":
            continue
        # Try to get the tool-specific prompt from Langfuse
        logger.debug(f"Fetching tool description for {tool} in {locale}.")
        prompt: PromptTemplate = LiteLLM(model_name="llama-4").get_langfuse_prompt(
            "competence-tool-" + tool + "-" + locale.value.lower(),
            chat=[],
            prompt_type="text",
            label=langfuse_label,
        )
        description = prompt.format()
        tool_descriptions.append(description)

    tool_list = "\n".join(f"- {tool}" for tool in tools)
    tool_descriptions_text = "\n\n".join(tool_descriptions)

    return tool_list, tool_descriptions_text


async def source_from_document(doc: Document, db: Database) -> Source:
    """Create a Source object from a Document."""
    book_id = doc.metadata.get("book_id") or doc.metadata.get("idbook")
    label = doc.id or doc.metadata.get("id", "Document")
    metadata = {}
    if book_id:
        [book, language] = await db.get_book_join_language(book_id)
        label = book.title
        metadata = {
            "publication_year": book.year,
            "authors": book.authors,
            "code": book.code,
            "title": book.title,
            "language": language.code if language else None,
        }
    page_content = doc.page_content.strip().replace('"', '\\"').replace("'", "\\'")
    if len(page_content) > 1000:
        page_content = page_content[:1000] + "... [truncated]"
    return Source(
        title=str(label), chunk=page_content, url=None, additional_metadata=metadata
    )


async def auto_retriever(
    messages: List[Message],
    retriever: SubDocRetriever,
    locale: LocaleType,
    competence_id: int,
    llm_client: BaseLLM | None = None,
    k=4,
) -> List[Document]:
    """Retrieve documents based on conversation history."""
    # Output parser will split the LLM result into a list of queries
    from langchain_core.output_parsers import BaseOutputParser

    class LineListOutputParser(BaseOutputParser[List[str]]):
        """Output parser for a list of lines."""

        def parse(self, text: str) -> List[str]:
            lines = text.strip().split("\n")
            lines = list(filter(None, lines))  # Remove empty lines
            if len(lines) > 4:
                lines = lines[-4:]  # Only keep last 4 lines
            return lines

    output_parser = LineListOutputParser()

    query_prompt = PromptTemplate(
        input_variables=["question"],
        template="""You are an AI language model assistant. Your task is to generate 
        four different versions of the given user question to retrieve relevant 
        documents from a vector database. By generating multiple perspectives on the 
        user question, your goal is to help the user overcome some of the limitations 
        of the distance-based similarity search. You are given a few conversation turns 
        to provide additional context to the question. Provide these alternative 
        questions separated by newlines. 
        
        Past Conversation Turns: {question}
        """,
    )

    # Chain
    llm_chain = query_prompt | llm_client.llm() | output_parser
    conversation = "\n".join(f"{msg.type}: {msg.content}" for msg in messages)

    queries = await llm_chain.ainvoke({"question": conversation})
    if not queries:
        logger.warning(
            "No queries generated from conversation: %s. Continuing with user query.",
            conversation,
        )
        queries = [messages[-1].content]  # Fallback to last user message

    docs_and_scores = []
    for query in queries:
        if query and len(query.strip()) > 0:
            retrived_docs_and_scores = await retriever.retrieve(
                query,
                competence_id=competence_id,
            )
            docs_and_scores.extend(retrived_docs_and_scores)

    docs_dict = {}
    for doc, score in docs_and_scores:
        doc_id = doc.id or doc.metadata.get("id", None)
        if doc_id not in docs_dict:
            docs_dict[doc_id] = (doc, score)
        elif docs_dict[doc_id][1] < score:
            docs_dict[doc_id] = (doc, score)

    docs_and_scores = list(docs_dict.values())
    docs_and_scores.sort(key=lambda x: x[1], reverse=False)

    docs = docs_and_scores[:k]  # Limit to top 4 documents

    if not docs:
        logger.warning("No documents found for queries: %s", queries)
        return []

    return [doc for doc, _ in docs]


def format_docs_with_id(docs: dict[int, Document]) -> str:
    """Format the documents with the source ID."""
    formatted = [  # \nArticle Title: {doc.metadata['title']}
        f"Source ID: {i}\nArticle Snippet: {doc.page_content}"
        for i, doc in docs.items()
    ]
    return "\n\n" + "\n\n".join(formatted)


def format_learning_unit(
    lu: LearningUnitCombined, prompt_template: PromptTemplate
) -> str:
    """Format the learning unit for the prompt."""
    return prompt_template.format(
        idlearningunit=lu.code,
        learning_goal=lu.learning_goal,
        task=lu.task,
        solution=lu.solution,
    )


def format_learning_goals(learning_units) -> str:
    """Format the given learning units to a list of learning goals."""
    return (
        "\n".join(f"- {lu.learning_goal}" for lu in learning_units)
        if learning_units
        else "N/A"
    )


def format_learning_units(
    learning_units: list[LearningUnitCombined], locale: LocaleType
) -> str:
    """Format the learning units for the prompt."""
    lu_format = get_localized_langfuse_prompt(
        "competence-learning-unit-format",
        locale,
        prompt_type="text",
    )

    learning_units_formatted = "\n\n".join(
        [format_learning_unit(lu, lu_format) for lu in learning_units]
    )
    return learning_units_formatted


async def get_relevant_learning_units(
    concept_id: int,
    cur_skill_level: int,
    aspired_skill_level: int,
    locale: LocaleType,
    db,
) -> list[LearningUnitCombined]:
    """Get relevant learning units for the current skill level."""
    learning_units = await db.get_learning_units_for_level(
        concept_id, aspired_skill_level, locale
    )
    return learning_units


def custom_tools_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["tools", "__end__", "formulate_answer", "tools_without_formulate_answer"]:
    """Custom condition function to determine the next step in the agent's graph.

    Based on the tools_condition by Langgraph.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
        ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        if len(ai_message.tool_calls) > 7:
            logger.warning("Too many tool calls in one message, concutting to 7.")
            ai_message.tool_calls = ai_message.tool_calls[:7]

        formulate_answer_called = any(
            tool_call.get("name") == "formulate_answer"
            or (
                hasattr(tool_call, "function")
                and tool_call.function.name == "formulate_answer"
            )
            for tool_call in ai_message.tool_calls
        )

        if formulate_answer_called:
            if len(ai_message.tool_calls) == 1:
                return "formulate_answer"
            else:
                # Remove formulate_answer tool call when other tools are also called
                return "tools_without_formulate_answer"
        return "tools"
    return "__end__"


def replace_tools(current: list[str], new: list[str]) -> list[str]:
    """Reducer that handles concurrent tool removal correctly.

    When multiple tools execute concurrently and each removes itself from
    the tools list, we need to ensure that all removals are preserved.
    This function keeps only tools that appear in both
    the current state and the new update (intersection).

    Args:
        current: The current tools list in state
        new: The updated tools list from a tool (with that tool removed)

    Returns:
        The intersection of current and new tools lists

    """
    if current is None or len(current) == 0:
        return new or []
    if new is None or len(new) == 0:
        return current or []

    return list(set(current) & set(new))


def merge_context(current: list, new: list) -> list:
    """Reducer that merges context lists, deletes duplicates.

    When multiple tools/nodes retrieve context concurrently,
    this ensures we don't have duplicate documents in the final context list.
    Uses idsubdocument from metadata as the unique identifier.

    Args:
        current: The current context list in state
        new: The new context list from a retrieval operation

    Returns:
        The merged context list without duplicates

    """
    if current is None or len(current) == 0:
        return new or []
    if new is None or len(new) == 0:
        return current or []

    # Create a dictionary to track unique documents by idsubdocument
    unique_docs = {}

    # First, add all current documents
    for doc in current:
        if hasattr(doc, "metadata") and doc.metadata:
            doc_id = doc.metadata.get("idsubdocument")
            if doc_id is not None:
                unique_docs[doc_id] = doc
            else:
                # Fallback for documents without idsubdocument - use content hash
                fallback_id = f"no_id_{hash(doc.page_content)}"
                unique_docs[fallback_id] = doc
        else:
            # Fallback for documents without metadata
            fallback_id = f"no_metadata_{hash(str(doc))}"
            unique_docs[fallback_id] = doc

    # Then, add new documents (will overwrite if same idsubdocument)
    for doc in new:
        if hasattr(doc, "metadata") and doc.metadata:
            doc_id = doc.metadata.get("idsubdocument")
            if doc_id is not None:
                unique_docs[doc_id] = doc
            else:
                # Fallback for documents without idsubdocument
                fallback_id = f"no_id_{hash(doc.page_content)}"
                unique_docs[fallback_id] = doc
        else:
            # Fallback for documents without metadata
            fallback_id = f"no_metadata_{hash(str(doc))}"
            unique_docs[fallback_id] = doc

    return list(unique_docs.values())


async def get_learning_units_to_test(
    request: RequestModel,
    db: Database,
) -> dict[str, list[LearningUnitCombined]]:
    """Get learning units to test based on the current competence and level."""
    learner_model: LearnerModel = await request.learner_model(db=db)

    completed_luids = []
    all_last_quizzed = []
    competences_to_test = request.storage.get("selected_competences", [])

    for lu in learner_model.learning_units.values():
        if lu.completed:
            completed_luids.append(lu.id)
        if lu.last_quizzed:
            all_last_quizzed.append(datetime.datetime.fromisoformat(lu.last_quizzed))

    last_quizzed = (
        max(all_last_quizzed)
        if all_last_quizzed
        else datetime.datetime.fromisoformat("1970-01-01T00:00:00Z")
    )

    # get all learning units seen since last quizzed
    new_lus_since_last_quiz = []
    quizzed_but_not_completed_lus = []
    new_lus_of_level = []
    if last_quizzed:
        # get all learning units seen since last quizzed
        seen_luids_since_last_quizzed = []
        quizzed_but_not_completed_luids = []
        all_seen_luids = []
        for lu in learner_model.learning_units.values():
            if (
                not lu.completed
                and lu.last_seen
                and datetime.datetime.fromisoformat(lu.last_seen) > last_quizzed
            ):
                seen_luids_since_last_quizzed.append(lu.id)

            if not lu.completed and lu.times_quizzed > 0:
                quizzed_but_not_completed_luids.append(lu.id)

            if lu.last_seen:
                all_seen_luids.append(lu.id)

        # and add them to the list of learning units to test
        if seen_luids_since_last_quizzed:
            new_lus_since_last_quiz.extend(
                await db.get_learning_units_joined_without_competences(
                    seen_luids_since_last_quizzed,
                    request.locale(),
                    only_competences=competences_to_test,
                )
            )
        if quizzed_but_not_completed_luids:
            # get learning units that are already quizzed but not yet completed
            quizzed_but_not_completed_lus = await db.get_learning_units_joined(
                quizzed_but_not_completed_luids, request.locale()
            )

        # get learning units of the current competence level that are not seen yet
        all_relevant_lus = await db.get_following_learning_units_for_learner_model(
            learner_model=learner_model,
            locale=request.locale(),
            only_competences=competences_to_test,
        )
        new_lus_of_level = [
            lu for lu in all_relevant_lus if lu.idlearningunit not in all_seen_luids
        ]

    return {
        "new_since_last_quiz": new_lus_since_last_quiz,
        "quizzed_but_not_completed": quizzed_but_not_completed_lus,
        "new_of_level": new_lus_of_level,
    }
