import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Literal, Union

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse, get_client
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from framework.api_types.ai_models import LLMPurpose
from framework.api_types.locale_type import LocaleType

sys.path.append(str(Path(__file__).parent.parent))

from bots.study.agents.db_retriever_agent import (
    get_relevant_learning_units,
    start_knowledge_graph_search,
)
from bots.study.agents.strategy_agent import update_conversation_strategy
from bots.study.agents.tools import (
    conclude,
    create_chunk,
    format_learner_model,
    formulate_answer,
    retrieve_additional_information,
    think,
    update_learner_model,
    update_memory_about_user,
)
from bots.study.helpers.helpers import (
    custom_tools_condition,
    get_llm,
    get_localized_langfuse_prompt,
    get_tool_descriptions_from_langfuse,
    localized,
)
from bots.study.helpers.models import StudyBotPostState, StudyBotState
from framework.api_types.choice import (
    MessageEvent,
)
from framework.api_types.request_format import (
    Message,
    MessageType,
    RequestModel,
)
from framework.chains.base_chain import BaseChain
from framework.db.database import Database
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever

logger = logging.getLogger()

graph_llm = None  # will be initialized lazily
thinking_llm = None  # will be initialized lazily

langfuse = get_client()


async def create_main_subgraph():
    """Create the main subgraph for the study agent."""
    tools = [
        think,
        retrieve_additional_information,
        # gauge_conversational_depth,
        formulate_answer,
        start_knowledge_graph_search,
        get_relevant_learning_units,
    ]
    tools_without_formulate_answer = [
        think,
        retrieve_additional_information,
        # gauge_conversational_depth,
        start_knowledge_graph_search,
        get_relevant_learning_units,
    ]
    tool_node = ToolNode(tools=tools)
    tools_without_formulate_answer = ToolNode(tools=tools_without_formulate_answer)
    answer_tool = formulate_answer
    formulate_answer_tool_node = ToolNode(tools=[answer_tool])

    # Adapt the system prompt based on the tools available
    async def initialize_main_state(state: StudyBotState, config: RunnableConfig):
        tool_names = [tool.name for tool in tools]
        configurable = config.get("configurable", {})
        request = configurable.get("request")
        db = configurable.get("db", None)
        sys_prompt, _ = await get_agent_prompt(request, tool_names, db=db)
        messages = state["messages"]
        messages[0] = sys_prompt
        return {"messages": messages, "context": []}

    tools_llm = graph_llm.bind_tools(tools)

    async def agent(state: StudyBotState):
        return {
            "messages": [await tools_llm.ainvoke(state["messages"])],
            "context": state.get("context", []),
        }

    async def force_formulate_answer_node(state: StudyBotState):
        messages = state["messages"]
        previous_agent_message = [
            message
            for message in messages
            if message.type == "assistant" or message.type == "ai"
        ][-1]
        messages.append(
            AIMessage(
                content="I will remember to use the `formulate_answer` tool to send a response to the user. Writing an answer without using it would be a mistake.",
                tool_calls=[
                    ToolCall(
                        name="formulate_answer",
                        args={
                            "task": previous_agent_message.content
                            or "Answer the user query. Align with the previous messages.",
                        },
                        id="chatcmpl-tool-force-formulate-answer",
                    )
                ],
            )
        )
        return {
            "messages": messages,
            "context": state.get("context", []),
        }

    subgraph_builder = StateGraph(StudyBotState)
    subgraph_builder.add_node("tools", tool_node)
    subgraph_builder.add_node("agent", agent)
    subgraph_builder.add_node("force_formulate_answer", force_formulate_answer_node)
    subgraph_builder.add_node("formulate_answer", formulate_answer_tool_node)
    subgraph_builder.add_node(
        "tools_without_formulate_answer", tools_without_formulate_answer
    )
    subgraph_builder.add_node("initialize_main_state", initialize_main_state)

    subgraph_builder.add_edge(START, "initialize_main_state")
    subgraph_builder.add_edge("initialize_main_state", "agent")
    subgraph_builder.add_conditional_edges(
        "agent",
        custom_tools_condition,
        {
            "tools": "tools",
            "__end__": "force_formulate_answer",
            "formulate_answer": "formulate_answer",
            "tools_without_formulate_answer": "tools_without_formulate_answer",
        },
    )
    subgraph_builder.add_edge("tools", "agent")
    subgraph_builder.add_edge("tools_without_formulate_answer", "agent")
    subgraph_builder.add_edge("force_formulate_answer", "formulate_answer")
    subgraph_builder.add_edge("formulate_answer", END)

    return subgraph_builder.compile()


def custom_post_tools_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["tools", "tools_into_end", "__end__"]:
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
        if len(ai_message.tool_calls) > 5:
            logger.warning("Too many tool calls in one message, concutting to 5.")
            ai_message.tool_calls = ai_message.tool_calls[:5]

        has_conclude = any(
            tool_call.get("name") == "conclude"
            or (
                hasattr(tool_call, "function") and tool_call.function.name == "conclude"
            )
            for tool_call in ai_message.tool_calls
        )

        if has_conclude:
            # If conclude is the only tool, end immediately
            if len(ai_message.tool_calls) == 1:
                return "__end__"
            else:
                return "tools_into_end"
        return "tools"
    return "__end__"


async def create_post_subgraph():
    """Create the main subgraph for the study agent."""
    post_tools = [
        update_conversation_strategy,
        update_memory_about_user,
        update_learner_model,
        think,
        conclude,
    ]
    post_tool_node = ToolNode(tools=post_tools)
    post_tool_node_into_end = ToolNode(tools=post_tools)

    # Used to force the agent to only call plan and update memory once each
    async def initialize_post_answer_state(
        state: StudyBotPostState, config: RunnableConfig
    ):
        # Extract tool names from post_tools list
        tool_names = [tool.name for tool in post_tools]
        return {"tools": tool_names}

    async def post_answer_agent(state: StudyBotPostState, config: RunnableConfig):
        selected_tools = [tool for tool in post_tools if tool.name in state["tools"]]
        # If think is the last tool, we end the conversation
        if len(selected_tools) <= 2 and all(
            tool.name in ["think", "conclude"] for tool in selected_tools
        ):
            return {"messages": "__end__"}

        messages = state["messages"]
        # Remove all system messages from state
        # Also replace the message by the thinking_agent, as it may confuse the post agent
        messages = [
            msg
            for msg in state["messages"]
            if not isinstance(msg, SystemMessage)
            and "YOU MUST FOLLOW THE FOLLOWING INSTRUCTIONS" not in msg.content
        ]

        # Check if second to last message is from assistant with "think" tool call
        if len(messages) >= 2:
            second_last_msg = messages[-2]
            if (
                hasattr(second_last_msg, "additional_kwargs")
                and "tool_calls" in second_last_msg.additional_kwargs
            ):
                tool_calls = second_last_msg.additional_kwargs["tool_calls"]
                for tool_call in tool_calls:
                    if (
                        tool_call.get("function", {}).get("name") == "think"
                        or tool_call.get("name") == "think"
                    ):
                        selected_tools = [
                            tool for tool in selected_tools if tool.name != "think"
                        ]
                        break

        tool_names = [tool.name for tool in selected_tools]
        configurable = config.get("configurable", {})
        request = configurable.get("request")
        db = configurable.get("db", None)

        sys_prompt, _ = await get_post_prompt(request, tool_names, db=db)
        messages.insert(0, sys_prompt)

        post_answer_llm = graph_llm.bind_tools(selected_tools)
        response = await post_answer_llm.ainvoke(messages)
        messages.append(response)
        return {"messages": messages}

    subgraph_builder = StateGraph(StudyBotPostState)
    subgraph_builder.add_node("post_tools", post_tool_node)
    subgraph_builder.add_node("post_answer_agent", post_answer_agent)
    subgraph_builder.add_node(
        "initialize_post_answer_state", initialize_post_answer_state
    )
    subgraph_builder.add_node("tools_into_end", post_tool_node_into_end)

    subgraph_builder.add_edge(START, "initialize_post_answer_state")
    subgraph_builder.add_edge("initialize_post_answer_state", "post_answer_agent")
    subgraph_builder.add_conditional_edges(
        "post_answer_agent",
        custom_post_tools_condition,
        {"tools": "post_tools", "tools_into_end": "tools_into_end", "__end__": END},
    )
    subgraph_builder.add_edge("post_tools", "post_answer_agent")
    subgraph_builder.add_edge("tools_into_end", END)
    subgraph_builder.add_edge("post_answer_agent", END)

    return subgraph_builder.compile()


async def create_study_graph(thinking_prompt) -> CompiledStateGraph:
    """Create a new study agent graph."""
    graph_builder = StateGraph(StudyBotState)

    async def thinking_agent(state: StudyBotState, config: RunnableConfig):
        messages = state["messages"]
        messages.insert(0, thinking_prompt)
        thinking_response = await thinking_llm.ainvoke(state["messages"])
        thinking_response.content += "\n\nRemember to use the `formulate_answer` tool to send a response to the user. Writing an answer without using it would be a mistake."
        thinking_response.content = (
            "YOU MUST FOLLOW THE FOLLOWING INSTRUCTIONS:\n" + thinking_response.content
        )
        messages.append(thinking_response)
        queue = config["configurable"].get("queue")
        request = config["configurable"].get("request")
        thread_id = config["configurable"].get("thread_id")

        event = MessageEvent(
            timestamp=datetime.now().isoformat(),
            event="think",
            additional_info={
                "thought_summary": localized(
                    request.locale(), "thinking_agent_finished"
                )
            },
        )
        if queue is not None:
            await queue.put(
                create_chunk(
                    instructions=[f"info: {event.model_dump_json()}"], msg_id=thread_id
                )
            )
        return {"messages": messages}

    graph_builder.add_node("thinking_agent", thinking_agent)

    main_subgraph = await create_main_subgraph()
    graph_builder.add_node("main_subgraph", main_subgraph)
    post_subgraph = await create_post_subgraph()
    graph_builder.add_node("post_subgraph", post_subgraph)

    graph_builder.add_edge(START, "thinking_agent")
    graph_builder.add_edge("thinking_agent", "main_subgraph")

    graph_builder.add_edge("main_subgraph", "post_subgraph")
    graph_builder.add_edge("post_subgraph", END)

    return graph_builder.compile()


async def stream_agent_and_queue(
    agent: CompiledStateGraph, agent_input: dict, queue: asyncio.Queue, config
) -> AsyncGenerator[str, None]:
    """Streams agent events and queue messages concurrently."""
    assert config is not None, "Config must be provided for streaming."
    thread_id = config.get("configurable", {}).get("thread_id")
    predefined_trace_id = Langfuse.create_trace_id(seed=thread_id)
    async def stream_agent_events():
        aggregated_message = ""
        try:
            with langfuse.start_as_current_observation(
                as_type="span",
                name="kira-lead-agent",
                trace_context={"trace_id": predefined_trace_id}
            ) as span:
                span.update_trace(
                    input=agent_input["messages"][-1] if "messages" in agent_input else agent_input
                )
                
                async for event in agent.astream_events(agent_input, config=config):
                    kind = event["event"]
                    # we dont want to stream the final agent output directly
                    # we use the formulate_answer tool to do that
                    if kind == "on_tool_end":
                        tool_output = event["data"].get("output")
                        if tool_output:
                            message_event = MessageEvent(
                                timestamp=datetime.now().isoformat(),
                                event="tool_completed",
                                additional_info={
                                    "name": event["name"] if "name" in event else "unknown"
                                },
                            )
                            yield create_chunk(
                                msg_id=thread_id,
                                instructions=[f"info: {message_event.model_dump_json()}"],
                            )
                            if event["name"] == "formulate_answer":
                                aggregated_message += tool_output.content
                span.update_trace(output={"response": aggregated_message})
        finally:
            # Always signal completion
            yield create_chunk(msg_id=thread_id, finish_reason="stop")
            await queue.put(None)

    async def stream_queue_messages():
        while True:
            message = await queue.get()
            if message is None:
                break
            yield message

    # Use an intermediate queue to merge both streams safely
    try:
        merged_queue = asyncio.Queue()
        agent_gen = stream_agent_events()
        queue_gen = stream_queue_messages()

        # Function to pump items from a generator into the merged queue
        async def pump_generator(gen, name):
            try:
                async for item in gen:
                    await merged_queue.put((name, item))
            except Exception as e:
                logger.error(f"Error in {name} generator: {e}")
            finally:
                await merged_queue.put((name, None))  # Signal this generator is done

        # Start both generators as background tasks
        agent_task = asyncio.create_task(pump_generator(agent_gen, "agent"))
        queue_task = asyncio.create_task(pump_generator(queue_gen, "queue"))

        # Track which generators are done
        finished_generators = set()

        # Consume from merged queue until both generators are done
        while len(finished_generators) < 2:
            try:
                name, item = await merged_queue.get()

                if item is None:
                    # This generator is finished
                    finished_generators.add(name)
                else:
                    # Yield the item
                    yield item

            except Exception as e:
                logger.error(f"Error consuming merged queue: {e}")
                break

        # Wait for both tasks to complete
        await asyncio.gather(agent_task, queue_task, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error in stream_agent_and_queue: {e}")
        raise


async def stream_open_conversation_agent(
    request: RequestModel, db: Database, retriever: SubDocRetriever
) -> AsyncGenerator[str, None]:
    """Handle a chat request using the agent."""
    global graph_llm, thinking_llm
    if not graph_llm:
        graph_llm = (
            await get_llm(LocaleType.EN, requested_purpose=LLMPurpose.AGENT)
        ).llm_chatopenai()
    if not thinking_llm:
        thinking_llm = (
            await get_llm(LocaleType.EN, requested_purpose=LLMPurpose.AGENT_THINK)
        ).llm_chatopenai()

    queue = asyncio.Queue()
    thread_id = f"{request.find_store('chat_id', '1')}-{request.id}"
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="starting_agent",
        additional_info={},
    )
    yield create_chunk(
        msg_id=thread_id,
        request=request,
        instructions=[f"info: {event.model_dump_json()}"],
        trace_id=Langfuse.create_trace_id(seed=thread_id)
    )

    max_iterations = 10
    recursion_limit = 2 * max_iterations + 1

    messages = request.chat_history
    locale = request.locale()
    selected_competence_code = request.find_store("selected_competence", None)

    cur_competence = await db.get_competence_translated_by_code(
        selected_competence_code, locale
    )

    conversation_history, _ = process_chat_history(messages)
    messages = [
        {
            "role": msg.type.value,
            "content": msg.content
            + f"\nDate: {datetime.fromisoformat(msg.timestamp).strftime('%Y-%m-%d')}",
        }
        for msg in conversation_history
        if msg.content.strip() != ""
    ]

    user_message = [
        msg for msg in request.chat_history[::-1] if msg.type == MessageType.USER
    ][0].content or ""

    thinking_prompt, config_dict = await get_thinking_prompt(
        request, db, user_message
    )  # maybe move prompt creation to graph nodes
    agent = await create_study_graph(thinking_prompt)
    config = {
        "recursion_limit": recursion_limit,
        "callbacks": [BaseChain.get_langfuse_callback()],
        "configurable": {
            **config_dict,
            "locale": locale,
            "competence_id": cur_competence.idcompetence if cur_competence else None,
            "queue": queue,
            "thread_id": thread_id,
            "db": db,
            "retriever": retriever,
            "request": request,
        },
        "metadata": {
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "coach_agent"],
        },
    }
    agent = agent.with_config(
        recursion_limit=recursion_limit,
        callbacks=[BaseChain.get_langfuse_callback()],
        configurable={
            **config_dict,
            "locale": locale,
            "competence_id": cur_competence.idcompetence if cur_competence else None,
            "queue": queue,
            "thread_id": thread_id,
            "db": db,
            "retriever": retriever,
            "request": request,
        },
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "coach_agent"],
        },
    )

    # Walk backwards through messages to find the last summary

    try:
        async for chunk in stream_agent_and_queue(
            agent,
            {"messages": messages},
            queue,
            config=config,
        ):
            yield chunk

    except GraphRecursionError as e:
        logger.error(f"Agent stopped due to max iterations: {e}")
        yield create_chunk(msg_id=thread_id, request=request, message=f"Error: {e}")
    finally:
        yield create_chunk(
            finish_reason="stop",
            msg_id=thread_id,
        )
        return


def process_chat_history(messages):
    """Walk through the messages in reverse order to find the last summary."""
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

    conversation_history = [
        msg for msg in conversation_history if msg.content.strip() != ""
    ]
    return conversation_history, includes_summary


async def get_agent_prompt(
    request: RequestModel,
    tools: list = None,
    prompt_name: str = "competence-lead-agent",
    db=None,
) -> tuple[SystemMessage, dict]:
    """Build the prompt for the agent."""
    locale = request.locale()
    user_memory = request.find_store("user_memory", "Currently no memory saved.")
    learner_model = await request.learner_model(db=db)
    conversation_strategy = request.find_store(
        "conversation_strategy", "No strategy available."
    )

    tool_list, tool_descriptions = get_tool_descriptions_from_langfuse(locale, tools)

    # Get the prompt template
    agent_prompt: ChatPromptTemplate = get_localized_langfuse_prompt(
        prompt_name,
        locale=locale,
        response_preferences=request.response_preferences,
    )

    learner_model_formatted = format_learner_model(learner_model)

    # Fill the prompt template with values
    config = {
        "topic": "N/A",
        "learner_model": learner_model_formatted,
        "user_memory": user_memory,
        "tool_list": tool_list,
        "tool_descriptions": tool_descriptions,
        "conversation_strategy": conversation_strategy,
        # "includes_ summary": includes_summary_text if includes_summary else "",
    }

    messages = agent_prompt.format_messages(**config)
    return messages[0], config


async def get_thinking_prompt(request: RequestModel, db, user_message):
    """Build the prompt for the thinking loop."""
    locale = request.locale()
    user_memory = request.find_store("user_memory", "Currently no memory saved.")

    learner_model = await request.learner_model(db=db)
    conversation_strategy = request.find_store(
        "conversation_strategy", "No strategy available."
    )
    learner_model_formatted = format_learner_model(learner_model)

    # Get the prompt template
    agent_prompt: ChatPromptTemplate = get_localized_langfuse_prompt(
        "competence-think-loop",
        locale=locale,
        response_preferences=request.response_preferences,
    )
    config = {
        "learner_model": learner_model_formatted,
        "user_memory": user_memory,
        "conversation_strategy": conversation_strategy,
        "user_message": user_message,
    }
    messages = agent_prompt.format_messages(**config)

    return messages[0], config


async def get_post_prompt(request: RequestModel, tool_names: list[str], db=None):
    """Build the prompt for the post-answer loop."""
    locale = request.locale()
    user_memory = request.find_store("user_memory", "Currently no memory saved.")
    learner_model = await request.learner_model(db=db)
    conversation_strategy = request.find_store(
        "conversation_strategy", "No strategy available."
    )
    learner_model_formatted = format_learner_model(learner_model)

    tool_list, tool_descriptions = get_tool_descriptions_from_langfuse(
        locale, tool_names
    )

    # Get the prompt template
    agent_prompt: ChatPromptTemplate = get_localized_langfuse_prompt(
        "competence-post-loop",
        locale=locale,
        response_preferences=request.response_preferences,
    )
    config = {
        "learner_model": learner_model_formatted,
        "user_memory": user_memory,
        "conversation_strategy": conversation_strategy,
        "tool_list": tool_list,
        "tool_descriptions": tool_descriptions,
    }
    messages = agent_prompt.format_messages(**config)

    return messages[0], config
