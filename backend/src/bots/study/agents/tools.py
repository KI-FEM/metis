import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnablePassthrough
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from bots.study.helpers.helpers import (
    format_docs_with_id,
    get_llm,
    get_localized_langfuse_prompt,
)
from bots.study.helpers.models import CitedAnswerDict, StudyBotPostState, StudyBotState
from framework.api_types.choice import (
    ChatCompletionsChunk,
    Choice,
    ChoiceDelta,
    MessageEvent,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import (
    LearnerModel,
    MessageType,
    RequestModel,
)
from framework.db.database import Database
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever

logger = logging.getLogger()


def create_chunk(
    request: RequestModel = None,
    message: str = None,
    instructions: List[str] = None,
    llm_model: str = None,
    sources: list = None,
    message_type: MessageType = MessageType.ASSISTANT,
    storage: dict = None,
    finish_reason: str = None,
    thoughts: str = None,
    citations: list[int] = None,
    trace_id: str = None,
    msg_id: str = None,
):
    """Yield a message to the event stream."""
    delta = ChoiceDelta()
    if message:
        delta.content = message
    if llm_model:
        delta.llm_model = llm_model
    if sources:
        delta.sources = sources
    if message_type:
        delta.type = message_type.value
    if instructions:
        delta.instructions = instructions
    if storage:
        delta.storage = storage
    if thoughts:
        delta.thoughts = thoughts
    if citations:
        delta.citations = citations
    if trace_id:
        delta.trace_id = trace_id
    # TODO: add buttons?

    if not msg_id:
        msg_id = f"{request.find_store('chat_id', '1')}-{request.id}"

    data_chunk = ChatCompletionsChunk(
        id=msg_id or "1",
        choices=[
            Choice(
                delta=delta,
                finish_reason=finish_reason if finish_reason else "",
            )
        ],
        created=datetime.now().isoformat(),
    )

    # send message
    return f"data: {data_chunk.model_dump_json()}\n\n"


@tool(parse_docstring=True)
async def think(config: RunnableConfig, thought: str, thought_summary: str) -> str:
    """Use the tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning or some cache memory is needed. Also provide a few words of summary for the user to see your progress.

    Args:
        thought: A thought to think about.
        thought_summary: A brief summary in a few words of the thought for easier reference.
    """
    queue = config["configurable"].get("queue", None)
    thread_id = config["configurable"].get("thread_id", None)
    logger.info(f"Thinking about: {thought}\nThought summary: {thought_summary}")
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="think",
        additional_info={"thought_summary": thought_summary},
    )
    if queue is not None:
        await queue.put(
            create_chunk(
                instructions=[f"info: {event.model_dump_json()}"], msg_id=thread_id
            )
        )
    return f"The following thought was saved: {thought}"


@tool(parse_docstring=True)
async def retrieve_additional_information(
    config: RunnableConfig,
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[StudyBotState, InjectedState],
) -> Command:
    """Retrieves documents from the knowledge graph based on a query. This tool is called *during* plan execution to gather more information, as specified by a step in the plan.

    Args:
        query: The query to search matching documents for in the knowledge graph.
    """
    topic_id = 1  # study_competence
    top_k = 4  # how many documents to retrieve

    queue = config["configurable"].get("queue")
    thread_id = config["configurable"].get("thread_id", None)
    locale: LocaleType = config["configurable"].get("locale", LocaleType.EN)
    logger.info(f"Retrieving documents for query: {query} in locale: {locale}")
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="retrieve_additional_information",
        additional_info={"query": query},
    )
    await queue.put(
        create_chunk(
            instructions=[f"info: {event.model_dump_json()}"], msg_id=thread_id
        )
    )

    db: Database = config["configurable"].get("db")
    retriever: SubDocRetriever = config["configurable"].get("retriever")

    language = await db.get_language(locale.value.lower())

    # retrieve
    retrieved = await retriever.retrieve(
        query=query,
        topic_id=topic_id,
        language_id=language.idlanguage,
    )
    retrieved_docs = [doc for doc, _ in retrieved]

    # rerank
    try:
        docs = await retriever.rerank(query, retrieved_docs)
    except Exception as e:
        # not fail the whole process if reranking fails
        logger.error(f"Error during reranking: {e}")
        docs = retrieved_docs

    docs = docs[:top_k]  # limit to top k documents

    return Command(
        update={
            "context": state.get("context", []) + docs,
            "messages": [
                ToolMessage(
                    f"Retrieved {len(docs)} documents for the query '{query}':\n{
                        '\n'.join(
                            [
                                f'**Document {i}**\n    {doc.page_content}'
                                for i, doc in enumerate(docs)
                            ]
                        )
                    }",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


@tool(parse_docstring=True)
async def formulate_answer(
    config: RunnableConfig,
    task: str,
    state: Annotated[StudyBotState, InjectedState],
    # tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Delegate the final answer formulation to a sub-agent by giving it a task. Be as specific as possible in how you want the task to be solved. Reference relevant documents and sources for the sub-agent to use. The sub-agent has ONLY access to the documents, NOT to the previous thought process. **Note:** Do NOT explictely mention learning unit IDs to the user, but only reference them in your reasoning process and the final answer. The user should only see the content / paraphrased result of the learning units, not their IDs.
    
    **Important:** This subagent must be called alone, without any other tool calls in the same turn.

    Args:
        task: The task for the sub-agent, so it can formulate the final answer according to your plan.
    """
    logger.info("Formulating answer to user...")
    queue = config["configurable"].get("queue")
    request = config["configurable"].get("request")
    thread_id = config["configurable"].get("thread_id", None)
    llm = await get_llm(locale=request.locale())
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="formulate_answer",
        additional_info={
            "llm": llm.model_name or "llama-4",
        },
    )
    await queue.put(
        create_chunk(
            instructions=[f"info: {event.model_dump_json()}"], msg_id=thread_id
        )
    )
    request: RequestModel = config["configurable"].get("request")

    previous_messages = [msg for msg in request.chat_history if len(msg.content) > 0]
    retrieved_prompt: ChatPromptTemplate = get_localized_langfuse_prompt(
        "competence-tool-formulate-answer",
        locale=config["configurable"].get("locale", "en"),
        response_preferences=request.response_preferences,
        prompt_type="chat",
        chat=previous_messages,
    )

    created_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: format_docs_with_id(x["context"]))
        )
        | retrieved_prompt
        | llm.llm_chatopenai().with_structured_output(CitedAnswerDict)
    )

    documents_in_order = dict(enumerate(state.get("context", [])))

    try:
        aggregated_message = ""
        async for event in created_chain.astream(
            {
                "task": task,
                "learner_model": config["configurable"].get("learner_model", {}),
                "user_memory": config["configurable"].get("user_memory", ""),
                "conversation_strategy": config["configurable"].get(
                    "conversation_strategy", ""
                ),
                "context": documents_in_order,
            }
        ):
            # if event["event"] == "on_chat_model_stream":
            answer = None
            reasoning_content = None
            citations = None
            chunk_content = event  # ["data"]["chunk"].content
            token = None
            if isinstance(chunk_content, str):
                # Try to parse as JSON first, in case it's a serialized dictionary
                try:
                    token = json.loads(chunk_content)
                except (json.JSONDecodeError, TypeError):
                    # If it's not valid JSON, treat it as a regular string
                    answer = aggregated_message + chunk_content
            else:
                token = chunk_content

            if token and isinstance(token, dict):
                if "answer" in token:
                    answer = token["answer"] or ""
                if "additional_kwargs" in token:
                    reasoning_content = token["additional_kwargs"].get(
                        "reasoning_content", ""
                    )
                if "citations" in token:
                    citations = token["citations"] or []
            # llama-4 seems to already aggregate the response
            aggregated_message = answer or aggregated_message
            await queue.put(
                create_chunk(
                    request=request,
                    message=answer or None,
                    thoughts=reasoning_content or None,
                    llm_model=llm.model_name,
                    citations=citations or None,
                    msg_id=thread_id,
                )
            )
            # if event["event"] == "on_chain_end":
        await queue.put(
            create_chunk(request=request, instructions=["answer_end"], msg_id=thread_id)
        )

        return f"Successfully composed and sent response:\n{aggregated_message}"
    except Exception as e:
        logger.error(f"Error during answer formulation: {e}")
        return f"Error during answer formulation: {e}"  # TODO: Cancel agent call here?


@tool(parse_docstring=True)
async def update_memory_about_user(
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
    state: Annotated[StudyBotPostState, InjectedState],
    memory: str,
) -> Command:
    """Builds a more complete memory of the user by adding new, relevant information. When using this tool, you must combine the user's existing memory with the new facts into a single, updated record.

    Args:
        memory: The updated memory about the user, combining existing knowledge with new, relevant information.
    """
    logger.info(f"Updating conversation memory: {memory}")
    thread_id = config["configurable"].get("thread_id", None)

    tools = list(state.get("tools", []))
    if "update_memory_about_user" in tools:
        tools.remove("update_memory_about_user")

    queue = config["configurable"].get("queue")
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="update_memory",
        additional_info={
            "new_memory": memory,
        },
    )
    await queue.put(
        create_chunk(
            instructions=[f"update_memory: {event.model_dump_json()}"], msg_id=thread_id
        )
    )
    return Command(
        update={
            "tools": tools,
            "messages": [
                ToolMessage(
                    f"User memory updated to '{memory}'", tool_call_id=tool_call_id
                )
            ],
        }
    )


@tool(parse_docstring=True)
async def update_learner_model(
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
    state: Annotated[StudyBotPostState, InjectedState],
    seen_learning_units: List[str],
) -> Command:
    """Records the user's interaction with specific knowledge concepts (Learning Units) to maintain an up-to-date and accurate model of their learning progress.

    This tool is the final step in the 'learning loop'. After information has been retrieved and an answer has been formulated and presented to the user, this tool should be called to formally log which concepts the user was exposed to in that turn. This updates metrics like 'last_seen_timestamp' and 'seen_count' for each Learning Unit.

    Args:
        seen_learning_units: A list of unique learning unit codes that were explicitly explained or directly referenced in the final answer provided to the user in the current turn.
    """
    logger.info(f"Updating learner model with: {seen_learning_units}")
    queue = config["configurable"].get("queue")
    thread_id = config["configurable"].get("thread_id", None)

    tools = list(state.get("tools", []))
    if "update_learner_model" in tools:
        tools.remove("update_learner_model")

    # use the seen learning units to update the learner model in the storage
    request: RequestModel = config["configurable"].get("request")
    db = config["configurable"].get("db")
    learner_model: LearnerModel = await request.learner_model(db=db)
    for lu in seen_learning_units:
        if lu in learner_model.learning_units:
            internal_lu = learner_model.learning_units[lu]
            internal_lu.times_seen += 1
            internal_lu.last_seen = datetime.now().isoformat()

    learner_model = learner_model.save_learner_model()
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="update_learner_model",
        additional_info={
            "seen_learner_model": seen_learning_units,
        },
    )
    await queue.put(
        create_chunk(
            instructions=[f"update_learner_model: {event.model_dump_json()}"],
            msg_id=thread_id,
        )
    )
    return Command(
        update={
            "tools": tools,
            "messages": [
                ToolMessage("Learner model updated.", tool_call_id=tool_call_id)
            ],
        }
    )


@tool(parse_docstring=True)
async def conclude(
    summary: str, tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Conclude the post-processing by finalizing all tasks. Use this tool, when no other tools need to be called anymore.

    Args:
        summary: A brief concluding summary of the agent's activities during the post-processing.
    """
    return Command(
        update={
            "tools": [],
            "messages": [
                ToolMessage("Execution finalized.", tool_call_id=tool_call_id)
            ],
        }
    )


def format_learner_model(
    learner_model: LearnerModel, include_quiz: bool = False
) -> str:
    """Format the learner model for display."""
    if isinstance(learner_model, LearnerModel):
        learner_model = learner_model.model_dump()

    learning_unit_format = """ - Learning Unit {code}
    * Completed: {completed}{not_completed_seen}{not_completed_quiz}"""

    learning_unit_format_not_completed_seen = """
    * Times Seen: {times_seen}
    * Last Seen: {last_seen}"""

    learning_unit_format_not_completed_quiz = """
    * Times Quizzed: {times_quizzed}
    * Times Correct: {times_correct}
    * Last Quizzed: {last_quizzed}"""

    concept_format = """ - Concept `{concept_code}`:\n{learning_units}"""
    competence_format = """ - Competence `{competence_code}` (Competence Level: {competence_level}):\n{concepts}"""

    competence_strings = []
    for competence in learner_model.get("competences", {}).values():
        concept_strings = []
        for concept_code, concept in competence.get("concepts", {}).items():
            learning_units = []
            for lu in concept.get("learning_units", {}).values():
                not_completed_seen = ""
                not_completed_quiz = ""
                if not lu.get("completed", False):
                    not_completed_seen = learning_unit_format_not_completed_seen.format(
                        times_seen=lu.get("times_seen", 0),
                        last_seen=lu.get("last_seen", "Never"),
                    )
                    if include_quiz:
                        not_completed_quiz = (
                            learning_unit_format_not_completed_quiz.format(
                                times_quizzed=lu.get("times_quizzed", 0),
                                times_correct=lu.get("times_correct", 0),
                                last_quizzed=lu.get("last_quizzed", "Never"),
                            )
                        )

                learning_units.append(
                    learning_unit_format.format(
                        code=lu.get("code", "N/A"),
                        completed="Yes" if lu.get("completed", False) else "No",
                        not_completed_seen=not_completed_seen,
                        not_completed_quiz=not_completed_quiz,
                    )
                )

            concept_strings.append(
                concept_format.format(
                    concept_code=concept_code,
                    competence_level=concept.get("competence_level"),
                    learning_units="\n".join(learning_units),
                )
            )
        competence_strings.append(
            competence_format.format(
                competence_code=competence.get("competence_code"),
                competence_level=competence.get("competence_level"),
                concepts="\n".join(concept_strings),
            )
        )

    learner_model_str = "\n".join(competence_strings)
    return learner_model_str
