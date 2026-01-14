import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict, Union

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import InjectedState, ToolNode
from langgraph.types import Command
from pydantic import BaseModel

from framework.api_types.ai_models import LLMPurpose

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from bots.study.agents.db_retriever_agent import (
    get_relevant_learning_units,
)
from bots.study.agents.tools import create_chunk, format_learner_model, think
from bots.study.helpers.helpers import get_llm, get_localized_langfuse_prompt
from bots.study.helpers.models import StudyBotPostState
from framework.api_types.choice import MessageEvent
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import (
    RequestModel,
)
from framework.chains.base_chain import BaseChain

logger = logging.getLogger()


async def start_strategy_agent(
    request: RequestModel,
    configurable: dict,
    response_reasoning: str,
    addressed_learning_units: list[int],
    messages: list,
):
    """Start a new study agent."""
    max_iterations = 10
    recursion_limit = 2 * max_iterations + 1

    agent_prompt = await get_strategy_agent_prompt(
        request, response_reasoning, addressed_learning_units
    )
    agent = await create_strategy_graph()

    config = {
        "recursion_limit": recursion_limit,
        "callbacks": [BaseChain.get_langfuse_callback()],
        "configurable": configurable, # Pass configurable from lead agent
        "metadata": {
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "strategy_agent"],
        },
    }
    agent = agent.with_config(
        recursion_limit=recursion_limit,
        callbacks=[BaseChain.get_langfuse_callback()],
        configurable=configurable,
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "strategy_agent"],
        },
    )
    clean_messages = [
        msg
        for msg in messages
        if not (isinstance(msg, AIMessage) and msg.additional_kwargs.get("tool_calls"))
        and not isinstance(msg, SystemMessage)
    ]
    agent_messages = [agent_prompt] + clean_messages
    try:
        response = await agent.ainvoke({"messages": agent_messages}, config=config)
        return response
    except GraphRecursionError as e:
        logger.error(f"Graph recursion error: {e}")
        return f"Error: The agent reached the maximum number of iterations ({max_iterations}). Please try rephrasing your request or ask for something simpler."
    except Exception as e:
        logger.error(f"Error in agent execution: {e}")
        return "Error: An unexpected error occurred during agent execution. Please try again later."


class StrategyState(TypedDict):
    """The state of the StudyBot Graph. Contains all messages."""

    messages: Annotated[list, add_messages]


async def create_strategy_graph() -> CompiledStateGraph:
    """Create the strategy agent graph."""
    graph_builder = StateGraph(StrategyState)

    tools = [think, get_relevant_learning_units, conclude]
    tool_node = ToolNode(tools=tools)
    conclude_tool_node = ToolNode(tools=[conclude])

    llm = (
        await get_llm(LocaleType.EN, requested_purpose=LLMPurpose.AGENT_STRATEGY)
    ).llm_chatopenai(temperature=0.7)

    tools_llm = llm.bind_tools(tools)

    async def agent(state: StrategyState):
        messages = state["messages"]
        response = await tools_llm.ainvoke(messages)
        messages.append(response)
        return {"messages": messages}

    def custom_tools_condition(
        state: Union[list[AnyMessage], dict[str, Any], BaseModel],
        messages_key: str = "messages",
    ) -> Literal["tools", "__end__"]:
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
            if any(
                tool_call.get("name") == "conclude"
                or (
                    hasattr(tool_call, "function")
                    and tool_call.function.name == "conclude"
                )
                for tool_call in ai_message.tool_calls
            ):
                return "conclude"
            return "tools"
        return "__end__"

    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("agent", agent)
    graph_builder.add_node("conclude", conclude_tool_node)

    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges(
        "agent",
        custom_tools_condition,
        {"tools": "tools", "conclude": "conclude", "__end__": END},
    )
    graph_builder.add_edge("tools", "agent")
    graph_builder.add_edge("conclude", END)

    return graph_builder.compile()


async def get_strategy_agent_prompt(
    request: RequestModel, response_reasoning: str, addressed_learning_units: list[int]
):
    """Get the prompt for the strategy agent."""
    locale = request.locale() or LocaleType.EN
    agent_prompt = get_localized_langfuse_prompt(
        "competence-strategy-agent", locale, request.response_preferences
    )

    # Fill the prompt template with values
    learner_model = await request.learner_model()
    agent_prompt_messages = agent_prompt.format_messages(
        learner_model=format_learner_model(learner_model),
        response_reasoning=response_reasoning,
        addressed_learning_units=", ".join(map(str, addressed_learning_units))
        if addressed_learning_units
        else "N/A",
        user_memory=request.find_store("user_memory", "Currently no memory saved."),
        conversation_strategy=request.find_store(
            "conversation_strategy",
            "There is currently no conversation strategy saved."
            if locale == LocaleType.EN
            else "Es ist derzeit keine Konversationsstrategie gespeichert.",
        ),
    )

    # Get only the system message part
    sys_message = agent_prompt_messages[0]
    return sys_message


@tool(parse_docstring=True)
async def conclude(
    conversation_strategy: str,
) -> str:
    """Use this tool to conclude your work and provide the final answer to the requester.

    Args:
        conversation_strategy: The final conversation strategy to be sent to the requester.
    """
    return f"Final Conclusion:\n{conversation_strategy}"


@tool(parse_docstring=True)
async def update_conversation_strategy(
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
    state: Annotated[StudyBotPostState, InjectedState],
    response_reasoning: str,
    addressed_learning_units: list[str],
) -> Command:
    """Reports the last conversational turn to the strategist sub-agent.

    This is the primary background tool for keeping the 'conversation_strategy'
    up-to-date. After a meaningful conversational turn, call this function
    to provide the strategist with an analysis of that turn. The strategist will
    then decide if a minor log update or a full strategic replan is needed.

    Args:
        response_reasoning: A summary of the strategic goal of the response you just sent. For example: "The goal was to validate the user's frustration and signal a pivot in our strategy."
        addressed_learning_units: A list of learning_unit IDs that were directly used or referenced in your last response. Provide an empty list `[]` if no units were used.
    """
    tools = list(state.get("tools", []))
    if "update_conversation_strategy" in tools:
        tools.remove("update_conversation_strategy")
    configurable = config.get("configurable", {})
    request = configurable.get("request")
    thread_id = configurable.get("thread_id")
    queue = configurable.get("queue")
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="update_conversation_strategy",
    )
    await queue.put(
        create_chunk(
            request=request,
            instructions=[f"info: {event.model_dump_json()}"],
            msg_id=thread_id,
        )
    )

    # get all messages for now TODO
    messages = state.get("messages", [])
    response = await start_strategy_agent(
        request, configurable, response_reasoning, addressed_learning_units, messages
    )

    # Check if response is a string (error case) or dict (success case)
    if isinstance(response, str):
        # this is an error message, so we keep the old strategy
        strategy = request.find_store("conversation_strategy", "No strategy available.")
    else:
        strategy = response["messages"][-1].content

    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="updated_conversation_strategy",
        additional_info={
            "conversation_strategy": strategy,
        },
    )
    await queue.put(
        create_chunk(
            request=request,
            instructions=[f"updated_conversation_strategy: {event.model_dump_json()}"],
            msg_id=thread_id,
        )
    )

    return Command(
        update={
            "tools": tools,
            "messages": [
                ToolMessage(
                    f"The following strategy was saved: \n#{strategy}",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
