import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, TypedDict, Union

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from framework.api_types.ai_models import LLMPurpose
from framework.api_types.choice import MessageEvent

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from bots.study.agents.tools import create_chunk, format_learner_model, think
from bots.study.helpers.helpers import (
    format_learning_units,
    get_llm,
    get_localized_langfuse_prompt,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import (
    LearnerModel,
    RequestModel,
)
from framework.chains.base_chain import BaseChain
from framework.db.database import Database

logger = logging.getLogger()

DB_SCHEMA_JSON = Path(__file__).parent / "db_schema.json"

# AGENT


async def start_db_agent(
    request: RequestModel,
    db: Database,
    configurable: dict,
    agent_task: str,
    additional_tools: list = None,
):
    """Start a new study agent."""
    if additional_tools is None:
        additional_tools = []

    max_iterations = 10
    recursion_limit = 2 * max_iterations + 1

    agent_prompt = await get_db_agent_prompt(request, db, agent_task)

    agent = await create_db_agent()

    config = {
        "recursion_limit": recursion_limit,
        "callbacks": [BaseChain.get_langfuse_callback()],
        "configurable": configurable,  # Pass configurable from lead agent
        "metadata": {
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "db_agent"],
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
            "langfuse_tags": ["open_conversation", "db_agent"],
        },
    )

    messages = [agent_prompt, HumanMessage(f"Task: {agent_task}")]

    try:
        response = await agent.ainvoke({"messages": messages}, config=config)
        return response
    except GraphRecursionError as e:
        logger.error(f"Graph recursion error: {e}")
        return f"Error: The agent reached the maximum number of iterations ({max_iterations}). Please try rephrasing your request or ask for something simpler."
    except Exception as e:
        logger.error(f"Error in agent execution: {e}")
        return "Error: An unexpected error occurred during agent execution. Please try again later."


class RetrieverState(TypedDict):
    """The state of the StudyBot Graph. Contains all messages."""

    messages: Annotated[list, add_messages]


async def create_db_agent():
    """Create a new study agent."""
    graph_builder = StateGraph(RetrieverState)
    llm = (
        await get_llm(LocaleType.EN, requested_purpose=LLMPurpose.AGENT)
    ).llm_chatopenai(temperature=0.5)

    tools = [
        conclude,
        think,
        execute_query,
        get_relevant_learning_units,
        get_concepts_for_competence_code,
        get_all_competences,
    ]
    tool_node = ToolNode(tools=tools)
    conclude_tool_node = ToolNode(tools=[conclude])

    tools_llm = llm.bind_tools(tools)

    async def agent(state: RetrieverState):
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


@tool(parse_docstring=True)
async def conclude(
    conclusion: str,
    learning_unit_codes: list[str],
) -> str:
    """Use this tool to conclude your work and provide the final answer to the requester.

    Args:
        conclusion: The final answer to be sent to the requester.
        learning_unit_codes: A list of learning unit codes that are relevant to the conclusion.
    """
    return f"Final Conclusion:\n{conclusion}\n\nRelevant Learning Units:\n" + ", ".join(
        learning_unit_codes
    )


@tool(parse_docstring=True)
async def start_knowledge_graph_search(
    config: RunnableConfig,
    search_task: str,
) -> str:
    r"""Use this tool to retrieve complex information from the knowledge graph database which contains the domain model modelling the knowledge that the user should acquire on a given topic. This tool is called when you need to gather specific information to answer the user's request or to inform your reasoning process. As a sub-agent will perform the actual search and return the results to you, this call is very expensive, so be as detailed as possible in describing what you want to retrieve and when to use the tool.

    Args:
        search_task: A detailed description of the information you want to retrieve from the database. For example 'Give me an overview over all learning units of the competence `resilience` that relate to 'social context' and only those that the user has not yet seen. First write a summary, then list the learning units with their titles and short descriptions.'
    """
    logger.info(f"Starting knowledge graph search with: {search_task}")

    request = config["configurable"].get("request")
    thread_id = config["configurable"].get("thread_id")
    db: Database = config["configurable"].get("db")
    configurable = config["configurable"]
    queue = config["configurable"].get("queue")
    if queue:
        event = MessageEvent(
            timestamp=datetime.now().isoformat(),
            event="start_knowledge_graph_search",
            additional_info={
                "search_task": search_task,
            },
        )
        await queue.put(
            create_chunk(
                msg_id=thread_id,
                request=request,
                instructions=[f"info: {event.model_dump_json()}"],
            )
        )

    response = await start_db_agent(request, db, configurable, search_task)
    if isinstance(response, str):
        report = response  # Error message
    else:
        report = response["messages"][-1].content
    return f"Knowledge graph search returned a response for the following task:\n**Task:** {search_task}\n\n**Response:** {report}"


@tool(parse_docstring=True)
async def get_relevant_learning_units(
    config: RunnableConfig,
    competence_code: Optional[str] = None,
    concept_code: Optional[str] = None,
    competence_level: Optional[int] = None,
    uncompleted_only: bool = True,
    completed_only: bool = False,
    localization: LocaleType = LocaleType.EN,
) -> str:
    """Use this tool to easily retrieve relevant learning units for a number of set parameters.

    This is more useful and less expensive than starting a knowledge graph search or executing raw SQL queries if you only need to get learning units, as it abstracts away the database structure and handles writing the queries for you.

    Args:
        competence_code: The code of the competence to retrieve learning units for. (EITHER this or concept_code).
        concept_code: The code of the concept to retrieve learning units for. (EITHER this or competence_code).
        competence_level: The competence level (1-4) to retrieve learning units for (OPTIONAL, defaults to all).
        uncompleted_only: Whether to retrieve only uncompleted learning units. (OPTIONAL, default: True).
        completed_only: Whether to retrieve only completed learning units. (OPTIONAL, default: False).
        localization: The localization/language for the learning units. (OPTIONAL, default: EN).
    """
    if competence_code and concept_code:
        return "Error: You must provide either competence_code or concept_code, but not both."
    if not competence_code and not concept_code:
        return "Error: You must provide either competence_code or concept_code."
    if uncompleted_only and completed_only:
        return "Error: You cannot set both uncompleted_only and completed_only to True."

    db: Database = config["configurable"].get("db")
    request: RequestModel = config["configurable"].get("request")
    thread_id = config["configurable"].get("thread_id")
    learner_model: LearnerModel = await request.learner_model(db=db)

    retrieved_learning_units = []
    completed_luids = []
    if uncompleted_only or completed_only:
        try:
            completed_luids = learner_model.get_completed_luids()
        except Exception:
            # Fallback if not Learner Model instance
            if isinstance(learner_model, dict):
                for competence in learner_model.get("competences", {}).values():
                    for concept in competence.get("concepts", {}).values():
                        completed_luids.extend(
                            [
                                lu.get("id")
                                for lu in concept.get("learning_units", {}).values()
                                if lu.get("completed")
                            ]
                        )
            else:
                logger.warning(
                    "Learner model is neither LearnerModel instance nor dict; cannot extract completed LU IDs."
                )
                return "Error: Unable to determine completed learning units from learner model."

    if competence_code:
        lus = await db.get_learning_units_for_competence_and_level(
            competence_id=(
                await db.get_competence_by_code(competence_code)
            ).idcompetence,
            competence_level_id=competence_level,
            locale=localization,
            excluded_luids=completed_luids if uncompleted_only else None,
            only_luids=completed_luids if completed_only else None,
        )
        retrieved_learning_units.extend(lus)
    elif concept_code:
        lus = await db.get_learning_units_for_level(
            concept_id=(await db.get_concept_by_code(concept_code)).idconcept,
            competence_level_id=competence_level,
            locale=localization,
            excluded_luids=completed_luids if uncompleted_only else None,
            only_luids=completed_luids if completed_only else None,
        )
        retrieved_learning_units.extend(lus)

    queue = config["configurable"].get("queue")
    if queue:
        event = MessageEvent(
            timestamp=datetime.now().isoformat(),
            event="get_relevant_learning_units",
            additional_info={
                "competence_level": competence_level,
                "competence_code": competence_code,
                "concept_code": concept_code,
                "uncompleted_only": uncompleted_only,
                "completed_only": completed_only,
                "localization": localization.value,
            },
        )
        await queue.put(
            create_chunk(
                msg_id=thread_id,
                request=request,
                instructions=[f"info: {event.model_dump_json()}"],
            )
        )

    formatted = format_learning_units(
        learning_units=retrieved_learning_units,
        locale=localization,
    )
    return "Retrieved Learning Units:\n" + formatted


def read_db_schema() -> str:
    """Read the database schema from the JSON file."""
    return DB_SCHEMA_JSON.read_text()


async def get_db_agent_prompt(request: RequestModel, db: Database, agent_task: str):
    """Get the prompt for the DB agent."""
    locale = request.locale() or LocaleType.EN
    agent_prompt = get_localized_langfuse_prompt(
        "competence-db-agent", locale, request.response_preferences
    )

    # Fill the prompt template with values
    learner_model = await request.learner_model(db=db)
    agent_prompt_messages = agent_prompt.format_messages(
        task=agent_task,
        database_schema=read_db_schema(),
        learner_model=format_learner_model(learner_model),
    )

    # Get only the system message part
    sys_message = agent_prompt_messages[0]
    return sys_message


# TOOLS


@tool(parse_docstring=True)
async def execute_query(config: RunnableConfig, goal: str, reasoning: str, query: str):
    """EXPENSIVE and ERROR-PRONE tool to execute a SQL query against the study database. You only have access to queries that retrieve data, such as SELECT statements, other queries will FAIL.

    Args:
        goal: The goal of what you are trying to achieve with this query.
        reasoning: Your reasoning for why you are executing this query and why this query is correctly written to retrieve exactly what your goal is.
        query: The SQL query to execute. Only SELECT queries are allowed. Check the database schema for available tables and columns.
    """
    db: Database = config["configurable"].get("db")
    if not query.strip().lower().startswith("select"):
        return "Error: Only SELECT queries are allowed."
    try:
        results = await db.execute(query)
        if not results:
            return "Query executed successfully, but no results were found."

        # Format results as a table
        if isinstance(results[0], dict):
            # If results are dictionaries
            headers = results[0].keys()
            table = " | ".join(headers) + "\n"
            table += "-|-".join(["---"] * len(headers)) + "\n"
            for row in results:
                table += " | ".join(str(row[h]) for h in headers) + "\n"
        else:
            # If results are tuples, create a simple numbered table
            table = "Row | Values\n"
            table += "--- | ---\n"
            for i, row in enumerate(results):
                table += f"{i + 1} | " + " | ".join(str(val) for val in row) + "\n"
        return f"Query executed successfully.\n- Query: {query}\n- Results:\n{table}"
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return f"Error executing query: {e}"


@tool(parse_docstring=True)
async def get_all_competences(config: RunnableConfig):
    """Use this tool to retrieve all competences available in the system. A competence is a specific skill or knowledge area that a learner can develop.

    Args:
    """
    db: Database = config["configurable"].get("db")
    competences = await db.get_competences_translated_light(
        config.get("locale", LocaleType.EN)
    )
    competences_str = "\n".join(
        [
            f"""- Competence `{comp.code}`:
    * Code: {comp.code}
    * Name: {comp.name}
    * Description: {comp.description}"""
            for comp in competences
        ]
    )
    return f"Retrieved {len(competences)} competences:\n{competences_str}"


@tool(parse_docstring=True)
async def get_concepts_for_competence_code(
    competence_code: str,
    config: RunnableConfig,
):
    """Use this tool to retrieve all concepts associated with a given competence code. A concept is a specific idea or topic that is part of a competence.

    Args:
        competence_code: The code of the competence to retrieve concepts for.
    """
    db: Database = config["configurable"].get("db")
    concepts = await db.get_concepts_for_competence_code(
        competence_code, config.get("locale", LocaleType.EN)
    )
    if not concepts:
        return f"No concepts found for competence code {competence_code}."
    concepts_str = "\n".join(
        [
            f"""- Concept `{concept.code}`:
    * Code: {concept.code}
    * Name: {concept.name}
    * Description: {concept.description}"""
            for concept in concepts
        ]
    )
    return f"Retrieved {len(concepts)} concepts for competence code {competence_code}:\n{concepts_str}"
