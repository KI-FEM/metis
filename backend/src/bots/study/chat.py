import json
import logging
import sys
from pathlib import Path
from typing import Union

from langchain_core.runnables import RunnablePassthrough
from langfuse.langchain import CallbackHandler

# Add src/ directory to path for module imports
sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import ResponseGenerationData
from bots.study.helpers.data_retriever import get_questions
from bots.study.helpers.helpers import (
    TOPIC_CODE,
    auto_retriever,
    format_docs_with_id,
    format_learning_goals,
    get_llm,
    get_localized_langfuse_prompt,
    localized,
    source_from_document,
)
from bots.study.helpers.models import CitedAnswerDict, InspirationsDict
from framework.api_types.request_format import (
    LearnerModel,
    Message,
    MessageType,
    RequestModel,
)
from framework.api_types.response_format import (
    MessageResponse,
    Response,
)
from framework.chains.base_chain import BaseChain
from framework.chains.passthrough_chain import PassthroughChain
from framework.db.database import Database
from framework.llm.base_llm import BaseLLM
from framework.llm.lite_llm import LiteLLM

logger = logging.getLogger()


async def open_conversation_base(
    request: RequestModel, bot_id, db: Database, vector_db, retriever
) -> Union[ResponseGenerationData, Response]:
    """Prerequisites for the open conversation functions."""
    # I'M NOT GONNA UPDATE THIS WHILE WE WORK ON THE AGENT,
    # IF WE NEED IT WE UPDATE IT LATER

    # get necessary information
    locale = request.locale()
    messages = request.chat_history
    selected_competence_code = request.find_store("selected_competence", None)
    bot_initiative = request.find_store("initiative", "user")
    selected_level_id = request.find_store("skill_level")
    learner_model: LearnerModel = await request.learner_model(db=db)

    completed_luids = [  # THIS WILL NOT WORK ATM
        lu.id
        for lu in learner_model.concepts[selected_competence_code].learning_units
        if lu.completed
    ]

    if not selected_competence_code:
        logger.error("No competence selected.")
        return Response(
            messages=[
                MessageResponse(
                    content=localized(locale, "no_competence_selected"),
                )
            ]
        )

    cur_competence = await db.get_competence_translated_by_code(
        selected_competence_code, locale
    )
    cur_level = await db.get_competence_level_translated(selected_level_id, locale)
    next_level = await db.get_competence_level_translated(
        cur_level.idcompetencelevel + 1, locale
    )
    completed_learning_units = await db.get_learning_units_joined(
        completed_luids, locale
    )
    next_learning_units = await db.get_following_learning_units(
        completed_luids,
        cur_competence.idcompetence,  # should be idconcept
        cur_level.idcompetencelevel,
        locale,
    )

    completed_learning_goals = format_learning_goals(completed_learning_units)
    next_learning_goals = format_learning_goals(next_learning_units)

    learning_goals = request.find_store("custom_learning_goals")
    _ = learning_goals  # TODO what to do with the learning goals?

    # Walk backwards through messages to find the last summary
    conversation_history = []
    includes_summary = False
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
            includes_summary = True
            break

    # If no summary was found, use all messages
    if not conversation_history:
        conversation_history = messages

    basic_chain_config = {
        "topic": selected_competence_code or "",
        "current_level": cur_level.name if cur_level else "N/A",
        "goal_level": next_level.name if next_level else "N/A",
        "previous_learning_goals": (
            completed_learning_goals if completed_learning_goals else "N/A"
        ),
        "learning_goals": next_learning_goals if next_learning_goals else "N/A",
    }

    requested_purpose = request.llm_purpose
    localized_llm = await get_llm(locale, requested_purpose)
    localized_llm_small: LiteLLM = await get_llm(locale, requested_purpose)

    if bot_initiative == "bot":
        # the user chose to let the bot take the initiative
        return open_conversation_base_bot_initiative(
            locale,
            localized_llm,
            localized_llm_small,
            request,
            conversation_history,
            basic_chain_config,
            vector_db,
            db,
            cur_competence,
        )

    # the user wrote a message and the bot should respond
    prompts = get_localized_langfuse_prompt(
        "competence-open-conversation",
        locale,
        request.response_preferences,
        chat=conversation_history,
        requested_llm=localized_llm,
    )

    # retrieve documents from the vector database based on the last user message
    # TODO: use more than the recent message to also have context
    # e.g. what happens when user simply said "what about the last topic?"
    last_few_messages = 5
    documents = await auto_retriever(
        messages[-last_few_messages:],  # last 5 messages
        retriever,
        locale,
        competence_id=cur_competence.idcompetence,
        llm_client=localized_llm,
        k=4,
    )

    documents_in_order = dict(enumerate(documents))

    # create the chain
    includes_summary_text = localized(locale, "includes_summary_text")
    chain_config = {
        **basic_chain_config,
        "context": documents_in_order,
        "includes_summary": includes_summary_text if includes_summary else "",
    }
    # TODO: makes reasoning LLMs not use their reasoning capabilities
    # Solution: 2-step approach: First let it reason in an unstructured way,
    # then use a second call with_structured_output to get the structured output
    structured_llm = localized_llm.llm_chatopenai().with_structured_output(
        CitedAnswerDict
    )

    created_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: format_docs_with_id(x["context"]))
        )
        | prompts
        | structured_llm
    ).with_config(
        callbacks=[BaseChain.get_langfuse_callback()],
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", bot_id],
        },
    )

    joined_chunks = await db.get_chunks_joined(
        [(d.metadata.get("idchunk")) for d in documents]
    )

    # ensure the sources are in the same order as the documents
    sources = {}
    for c in joined_chunks:
        doc_id = next(
            (
                i
                for i, doc in documents_in_order.items()
                if doc.metadata.get("idchunk") == c.chunk.idchunk
            ),
            None,
        )
        sources[doc_id] = c.source

    # return information to the caller
    return ResponseGenerationData(
        chain_config=chain_config,
        created_chain=created_chain,
        sources=sources,
        llm_model=localized_llm.get_model_name(),  # may be different if fallback
    )


async def open_conversation_base_bot_initiative(
    locale,
    requested_llm: BaseLLM,
    localized_llm_small,
    request: RequestModel,
    conversation_history,
    basic_chain_config,
    vector_db,
    db,
    cur_competence,
) -> ResponseGenerationData:
    """Method for creating bot response when the bot has the initiative.

    The user is able to say that the bot should take the initiative and ask questions.
    Then, the bot is instructed to select a topic and ask questions about it.
    """
    selected_competence = request.find_store("selected_competence", "")

    # TODO use with_structured_output to get model to adhere to the structure
    # Use the LLM to generate a search term for the selected competence and retrieve
    # documents from the vector database
    get_search_term_prompt = get_localized_langfuse_prompt(
        "competence-initiative-search-term",
        locale,
        request.response_preferences,
        requested_llm=requested_llm,
    )
    session_id = request.find_store("unique_id", request.find_store("chat_id", None))
    search_term_response = (
        await PassthroughChain()
        .create_chain(
            localized_llm_small.llm(max_tokens=200, chat_id=session_id),
            get_search_term_prompt,
            session_id=session_id,
        )
        .ainvoke({"topic": selected_competence})
    )
    rag_prompt = f"Give an overview over the topic {selected_competence}."  # fallback
    if '"search_term"' in search_term_response:
        try:
            start_index = search_term_response.index("{")
            end_index = search_term_response.rindex("}") + 1
            response_json = search_term_response[start_index:end_index].strip()
            rag_prompt = json.loads(response_json)["search_term"]
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to decode JSON: %s", search_term_response)
    else:
        logger.error("Failed to find search term in response: %s", search_term_response)

    # Using the retrieved documents, create the chain
    prompts = get_localized_langfuse_prompt(
        "competence-initiative",
        locale,
        request.response_preferences,
        chat=conversation_history,
        requested_llm=requested_llm,
    )
    documents = await vector_db.asimilarity_search(
        rag_prompt, competence_id=cur_competence.idcompetence
    )
    chain_config = {
        **basic_chain_config,
        "context": documents,
    }
    structured_llm = requested_llm.llm_chatopenai().with_structured_output(
        CitedAnswerDict
    )

    langfuse_handler = CallbackHandler()
    created_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: format_docs_with_id(x["context"]))
        )
        | prompts
        | structured_llm
    ).with_config(callbacks=[langfuse_handler])

    sources = {
        i: await source_from_document(doc, db) for i, doc in enumerate(documents)
    }

    # return information to the caller
    return ResponseGenerationData(
        chain_config=chain_config,
        created_chain=created_chain,
        sources=sources,
        llm_model=requested_llm.get_model_name(),
    )


async def generate_inspirations(
    request: RequestModel, bot_id: str, db: Database, retriever
) -> list[str]:
    """Generate contextual inspirations based on conversation history.

    This function analyzes the current conversation and retrieves relevant context
    to generate 3 thoughtful questions that the user might want to ask next.

    Args:
        request: The request containing conversation history and context
        bot_id: The bot identifier
        db: Database connection
        retriever: Vector database retriever

    Returns:
        List of 3 generated inspiration questions

    """
    locale = request.locale()
    response_preferences = request.response_preferences
    messages = request.chat_history

    # If no competence selected or no conversation history, return empty list
    if not messages:
        return []

    learner_model = await request.learner_model(db=db)

    next_learning_units = await db.get_following_learning_units_for_learner_model(
        learner_model, locale
    )
    next_learning_goals = format_learning_goals(next_learning_units)

    user_messages = [
        message for message in messages if message.type == MessageType.USER
    ]
    recent_user_message = user_messages[-1].content if len(user_messages) > 0 else None

    if recent_user_message:
        language = await db.get_language(locale.value)
        retrieved = await retriever.retrieve(
            query=recent_user_message,
            retrieve_count=5,
            language_id=language.idlanguage if language else None,
        )
        documents = [doc for doc, _ in retrieved]
        documents_in_order = dict(enumerate(documents))
    else:
        documents_in_order = {}

    llm = await get_llm(locale, request.llm_purpose)
    prompts = get_localized_langfuse_prompt(
        "competence-generate-inspirations",
        locale,
        response_preferences,
        chat=messages[-5:],
        requested_llm=llm,
    )
    structured_llm = llm.llm_chatopenai().with_structured_output(InspirationsDict)

    chain_config = {
        "context": documents_in_order,
        "topic": "study competence",
        "learning_goals": next_learning_goals,
    }

    # Create the chain with context
    langfuse_handler = CallbackHandler()
    chain = (
        RunnablePassthrough.assign(
            context=(lambda x: format_docs_with_id(x["context"]))
        )
        | prompts
        | structured_llm
    ).with_config(callbacks=[langfuse_handler])

    result = await chain.ainvoke(chain_config)

    # Handle string results that contain JSON
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            result = parsed
        except json.JSONDecodeError:
            pass

    if isinstance(result, dict) and "questions" in result:
        return result["questions"][:2]  # Ensure max 2 questions
    elif hasattr(result, "questions"):
        return result.questions[:2]  # Ensure max 2 questions
    else:
        logger.warning(
            "Unexpected result format from inspiration generation, "
            f"using static fallback: {result}"
        )
        questions = get_questions(TOPIC_CODE, locale)
        return questions
