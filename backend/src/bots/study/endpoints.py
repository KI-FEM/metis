import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnablePassthrough
from langfuse import Langfuse, get_client

from framework.db.database import Database

# Add src/ directory to path for module imports
sys.path.append(str(Path(__file__).parent.parent))
from bots.study.helpers.helpers import (
    get_llm,
    get_localized_langfuse_prompt,
    source_from_document,
)
from bots.study.helpers.models import (
    IntroductionDict,
)
from framework.api_types.choice import ChatCompletionsChunk, Choice, ChoiceDelta
from framework.api_types.request_format import (
    LearnerModelLearningUnit,
    MessageType,
    RequestModel,
)
from framework.api_types.response_format import (
    MessageResponse,
    MetaInformation,
    Response,
)
from framework.chains.base_chain import BaseChain

logger = logging.getLogger()
langfuse = get_client()

async def get_topic_intro(
    request: RequestModel, bot_id: str, db: Database, retriever
) -> Response | StreamingResponse:
    """Select a topic to learn about and give an introduction into the topic."""
    # doesnt work anymore
    selected_competence_code = request.find_store("selected_competence", None)
    session_id = request.find_store("unique_id", request.find_store("chat_id", None))
    locale = request.locale()
    selected_level_id = request.find_store("skill_level")
    learner_model: list[LearnerModelLearningUnit] = request.find_store(
        "learner_model", []
    )
    completed_luids = [lu.id for lu in learner_model if lu.completed]

    logger.info("StudyCompetenceBot: Competence selection")

    # Retrieve information relevant to personalization data from the DB
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
    completed_learning_goals = (
        "\n".join(lu.learning_goal for lu in completed_learning_units)
        if completed_learning_units
        else "N/A"
    )
    next_learning_goals = (
        "\n".join(lu.learning_goal for lu in next_learning_units)
        if next_learning_units
        else "N/A"
    )
    llm_client = await get_llm(locale, request.llm_purpose)

    # Retrieve documents useful for an introduction using a pre-written query retrieved
    # from Langfuse and filled with the selected competence
    langfuse_prompt = get_localized_langfuse_prompt(
        "competence-introduction-summarization",
        locale,
        request.response_preferences,
        requested_llm=llm_client,
        prompt_type="text",
    )

    language = await db.get_language(locale.value)
    query = langfuse_prompt.format(selected_topic=cur_competence.name)
    retrieved = await retriever.retrieve(
        query=query,
        competence_id=cur_competence.idcompetence,
        language_id=language.idlanguage if language else None,
    )
    docs = []

    if retrieved:
        # Process the retrieved documents
        docs_only = [doc for doc, _ in retrieved]
        top_k = 4
        reranked_docs = await retriever.rerank(
            query=query,
            retrieved_documents=docs_only,
        )
        docs = reranked_docs[:top_k]  # Limit to top_k documents

    # Build the chain for the introduction using a structured output
    summary = ""  # TODO? # get a pre-written summary of the topic
    chain_config = {
        "context": docs,
        "summary": summary,
        "topic": selected_competence_code,
        "current_level": cur_level.name if cur_level else "N/A",
        "goal_level": next_level.name if next_level else "N/A",
        "previous_learning_goals": (
            completed_learning_goals if completed_learning_goals else "N/A"
        ),
        "learning_goals": next_learning_goals if next_learning_goals else "N/A",
    }

    structured_llm = (
        llm_client.llm_chatopenai()
        .with_structured_output(IntroductionDict)
        .with_config(
            callbacks=[BaseChain.get_langfuse_callback()],
            metadata={
                "langfuse_session_id": session_id,
                "langfuse_tags": ["introduction", bot_id],
            },
        )
    )
    introduction_prompt = get_localized_langfuse_prompt(
        "competence-introduction",
        locale,
        request.response_preferences,
        requested_llm=llm_client,
    )

    created_chain = (
        RunnablePassthrough.assign(
            context=lambda x: "\n\n".join(doc.page_content for doc in x["context"])
        )
        | introduction_prompt
        | structured_llm
    )

    # Invoke the chain and send the response
    # Handle streaming and non-streaming responses separately (similar to chat)
    if request.streaming:

        async def stream_intro_message(
            request: RequestModel,
        ):
            """Stream a message."""
            timestamp = datetime.now().isoformat()
            trace_id = Langfuse.create_trace_id(seed=session_id + "-" + timestamp)
            # Send initial metadata
            first_chunk = ChatCompletionsChunk(
                id=session_id,
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            type=MessageType.ASSISTANT.value,
                            sources={
                                i: await source_from_document(doc, db)
                                for i, doc in enumerate(docs)
                            },
                            llm_model=llm_client.get_model_name(),
                            trace_id=trace_id
                        ),
                        finish_reason="",
                    )
                ],
                created=timestamp,
            )
            yield f"data: {first_chunk.model_dump_json()}\n\n"

            with langfuse.start_as_current_observation(
                as_type="span",
                name="kira-introduction",
                trace_context={"trace_id": trace_id},
            ):
                # Stream message content - similar to chat
                token_stream_iterator = created_chain.astream(chain_config)
                thinking = False

                async for token in token_stream_iterator:
                    introduction = ""
                    data_chunk = ChatCompletionsChunk(
                        id=session_id,
                        choices=[],
                        created=datetime.now().isoformat(),
                    )

                    if isinstance(token, dict):
                        if "introduction" in token:
                            introduction = token["introduction"]
                            data_chunk.choices.append(
                                Choice(
                                    delta=ChoiceDelta(content=introduction),
                                    finish_reason="",
                                )
                            )
                        else:
                            continue
                    else:
                        thought = ""
                        if "<think>" in token:
                            thinking = True
                            thought = token.split("<think>")[1]
                        if "</think>" in token:
                            thought = token.split("</think>")[0]

                        delta = ChoiceDelta(
                            content=token,
                        )
                        if thinking:
                            delta = ChoiceDelta(thoughts=thought)
                        data_chunk.choices.append(Choice(delta=delta, finish_reason=""))
                        if "</think>" in token:
                            thinking = False

                    yield f"data: {data_chunk.model_dump_json()}\n\n"

                # Send stop
                final_chunk = ChatCompletionsChunk(
                    id=session_id,
                    choices=[Choice(delta=ChoiceDelta(), finish_reason="stop")],
                    created=datetime.now().isoformat(),
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
        return StreamingResponse(
            stream_intro_message(request), media_type="text/event-stream"
        )
    else:
        # not streaming
        response = await created_chain.ainvoke(chain_config)

        # what if we have a reasoning model? Maybe let it reason in one call and then
        # summarize with a non-reasoning model and structured output?

        message = ""
        if isinstance(response, dict) and "introduction" in response:
            message = response["introduction"]
        elif isinstance(response, str):
            try:
                parsed_response = json.loads(response.strip())
                message = parsed_response.get("introduction", "")
            except json.JSONDecodeError:
                logger.error("Failed to parse response as JSON: %s", response)
                message = response

        # send the response
        message_response = MessageResponse(
            content=message,
            type="assistant",
            buttons=[],
            meta_information=MetaInformation(
                sources={
                    i: await source_from_document(doc, db) for i, doc in enumerate(docs)
                },
                llm_model=llm_client.get_model_name(),
            ),
        )
        return Response(messages=[message_response])
