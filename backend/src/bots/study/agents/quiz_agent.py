import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Literal, TypedDict, Union

from langchain.prompts import PromptTemplate
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, TypeAdapter
from typing_extensions import Annotated

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from bots.study.agents.lead_agent import process_chat_history, stream_agent_and_queue
from bots.study.agents.tools import (
    create_chunk,
    format_learner_model,
    retrieve_additional_information,
    think,
)
from bots.study.helpers.helpers import (
    custom_tools_condition,
    format_learning_units,
    get_learning_units_to_test,
    get_llm,
    get_localized_langfuse_prompt,
    get_tool_descriptions_from_langfuse,
)
from bots.study.helpers.models import QuizModelDict
from framework.api_types.ai_models import LLMPurpose
from framework.api_types.choice import (
    MessageEvent,
)
from framework.api_types.quiz_models import QuizModel, QuizType
from framework.api_types.request_format import (
    RequestModel,
)
from framework.chains.base_chain import BaseChain
from framework.db.database import Database
from framework.db.db_types import LearningUnitCombined

logger = logging.getLogger()

MAXSCORES = {
    QuizType.MULTIPLE_CHOICE: 1,
    QuizType.SLIDER: 1,
    QuizType.FILL_IN_BLANKS: 2,
    QuizType.FREETEXT: 3,
}


async def stream_quiz_agent(
    request: RequestModel, db: Database
) -> AsyncGenerator[str, None]:
    """Stream the quiz agent response."""
    queue = asyncio.Queue()
    thread_id = request.id
    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="starting_agent",
        additional_info={},
    )
    yield create_chunk(
        msg_id=thread_id,
        request=request,
        instructions=[f"info: {event.model_dump_json()}"],
    )

    logger.info(f"Starting quiz agent with request: {request}")

    max_iterations = 7
    recursion_limit = 2 * max_iterations + 1

    locale = request.locale()
    tools = [think, retrieve_additional_information]
    agent = await create_quiz_agent(request, db, tools)
    agent_prompt = await get_quiz_agent_prompt(request, db, tools=tools)
    config = {
        "recursion_limit": recursion_limit,
        "callbacks": [BaseChain.get_langfuse_callback()],
        "configurable": {
            "locale": locale,
            "thread_id": request.find_store("chat_id", "1"),
            "db": db,
            "request": request,
            "queue": queue,
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
            "locale": locale,
            "thread_id": request.find_store("chat_id", "1"),
            "db": db,
            "request": request,
            "queue": queue,
        },
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["open_conversation", "coach_agent"],
        },
    )

    conversation_history, _ = process_chat_history(request.chat_history)
    messages = [agent_prompt]
    messages.extend(
        [
            {"role": msg.type.value, "content": msg.content}
            for msg in conversation_history
        ]
    )

    event = MessageEvent(
        timestamp=datetime.now().isoformat(),
        event="quiz_generation_started",
        additional_info={},
    )
    chunk = create_chunk(
        msg_id=request.find_store("chat_id", "1"),
        request=request,
        instructions=[f"info: {event.model_dump_json()}"],
    )
    await queue.put(chunk)

    try:
        async for chunk in stream_agent_and_queue(
            agent,
            {
                "messages": messages,
                "quiz": None,
            },
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


class QuizState(TypedDict):
    """The state of the Quiz Agent. Contains all messages."""

    messages: Annotated[list, add_messages]
    quiz: Union[QuizModel, None] = None


async def create_quiz_agent(request: RequestModel, db: Database, tools):
    """Create a new quiz agent."""
    llm = (await get_llm(request.locale(), LLMPurpose.AGENT)).llm_chatopenai(
        temperature=0.5
    )

    tool_node = ToolNode(tools=tools)

    async def agent(state: QuizState, config: RunnableConfig):
        generated = await llm.ainvoke(state["messages"])
        
        queue = config["configurable"].get("queue")
        if queue:
            event = MessageEvent(
                timestamp=datetime.now().isoformat(),
                event="quiz_generated",
                additional_info={},
            )
            chunk = create_chunk(
                msg_id=request.id,
                request=request,
                instructions=[f"info: {event.model_dump_json()}"],
            )
            await queue.put(chunk)
        return {
            "messages": [generated],
        }

    async def verifier(state: QuizState, config: RunnableConfig):
        messages = state["messages"]
        generated_quiz_msg = messages[-1].content
        if "{" not in generated_quiz_msg or "}" not in generated_quiz_msg:
            messages.append(
                HumanMessage(
                    content="try_again The previous quiz was not a valid JSON. Please output the quiz in the correct JSON format.",
                )
            )
            return {
                "messages": messages,
            }
        try:
            json_part = generated_quiz_msg[
                generated_quiz_msg.index("{") : generated_quiz_msg.rfind("}")
            ]
            generated_quiz = json.loads(json_part)
            parsed_quiz: QuizModelDict = TypeAdapter(QuizModelDict).validate_json(
                generated_quiz
            )
            learning_units = [
                question.learning_unit for question in parsed_quiz.questions
            ]
        except Exception as _:
            # find all substrings that start with "LU_"
            learning_units = re.findall(r'LU_[a-zA-Z0-9_]+', generated_quiz_msg)
            learning_units = list(set(learning_units))

        # check if learning units exist

        lu_objs = await db.get_learning_units_joined_by_code(
            learning_units, request.locale()
        )
        if len(lu_objs) != len(learning_units):
            # some learning units not found
            # find the missing ones
            found_lu_codes = {lu.code for lu in lu_objs}
            missing_lus = [lu for lu in learning_units if lu not in found_lu_codes]
            messages.append(
                HumanMessage(
                    content=f"try_again The previous quiz contained learning units that do not exist in the learner model: {', '.join(missing_lus)}. Please correct the quiz and only use existing learning units.",
                )
            )
            return {
                "messages": messages,
            }

        sys_prompt = await get_verifier_prompt(request, db, lu_objs)
        messages[0] = sys_prompt

        class QuizVerifierResponse(TypedDict):
            reasoning: Annotated[
                str, ..., "Reasoning chain whether the quiz is valid or not."
            ]
            verdict: Annotated[
                Literal["valid", "try_again"],
                ...,
                "The final verdict whether the quiz is valid.",
            ]
        valid_verifier_response = False
        verifier_tries = 0
        response = None
        while not valid_verifier_response:
            response = await llm.with_structured_output(QuizVerifierResponse).ainvoke(
                state["messages"]
            )
            if "verdict" in response and "reasoning" in response:
                break
            verifier_tries += 1
            if verifier_tries >= 3:
                # give up
                response = {
                    "verdict": "valid",
                    "reasoning": "Could not determine validity after multiple tries. Assuming valid.",
                }
                break

        quiz_valid = response["verdict"] == "valid"
        if quiz_valid:
            messages.append(
                HumanMessage(
                    content=f"Valid quiz! Reasoning: {response['reasoning']}",
                )
            )
            queue = config["configurable"].get("queue")
            if queue:
                event = MessageEvent(
                    timestamp=datetime.now().isoformat(),
                    event="quiz_verified",
                    additional_info={},
                )
                chunk = create_chunk(
                    msg_id=request.id,
                    request=request,
                    instructions=[f"info: {event.model_dump_json()}"],
                )
                await queue.put(chunk)
        else:
            messages.append(
                HumanMessage(
                    content=f"try_again The quiz is not valid, please try again. Reasoning:\n{response['reasoning']}",
                )
            )
        return {
            "messages": messages,
        }

    async def json_formatter(state: QuizState):
        messages = state["messages"]
        quiz_message: str = messages[-2].content
        if "```json" in quiz_message:
            # the json is inside a code block
            generated_quiz = quiz_message[
                quiz_message.rfind("```json") + 7 : quiz_message.rfind("```")
            ].strip()
        elif "{" in quiz_message:
            # somewhere in the message, the json starts
            generated_quiz = quiz_message[
                quiz_message.index("{") : quiz_message.rfind("}")
            ].strip()
        else:
            messages.append(
                HumanMessage(
                    content="The previous quiz was not a valid JSON. Please output the quiz in the correct JSON format.",
                )
            )
            return {
                "messages": messages,
                "quiz": None,
            }
        try:
            parsed_quiz = TypeAdapter(QuizModelDict).validate_json(generated_quiz)

            return {
                "messages": messages,
                "quiz": parsed_quiz,
            }
        except Exception as e:
            # fallback: let the LLM try to fix the JSON
            messages.append(
                HumanMessage(
                    content=f"The previous quiz was not a valid JSON. Please output the quiz in the correct JSON format. Error details:\n{e}",
                )
            )
            return {
                "messages": messages,
                "quiz": None,
            }

    async def generate_json(state: QuizState):
        messages = state["messages"]

        class QuizJsonResponse(TypedDict):
            quiz: Annotated[
                QuizModelDict, ..., "The final quiz in the correct JSON format."
            ]
            
        tries = 1
        quiz = None
        while quiz is None and tries <= 3:
            response = await llm.with_structured_output(QuizJsonResponse).ainvoke(messages)
            quiz = response.get("quiz", None)
            if quiz is None:
                if response.get("title") is not None:
                    # maybe the LLM returned the quiz directly
                    try:
                        quiz = TypeAdapter(QuizModelDict).validate_python(response)
                    except Exception:
                        tries += 1
                        continue
        
        messages.append(
            HumanMessage(
                content=f"Final JSON output:\n{json.dumps(quiz, indent=2)}",
            )
        )
        return {
            "messages": messages,
            "quiz": quiz,
        }

    async def final_verifier(state: QuizState, config: RunnableConfig):
        messages = state["messages"]
        generated_quiz_msg: str = messages[-1].content
        generated_quiz = state["quiz"]
        try:
            if generated_quiz is None:
                json_part = generated_quiz_msg[
                    generated_quiz_msg.index("{") : generated_quiz_msg.rfind("}")
                ]
                generated_quiz = json.loads(json_part)

            parsed_quiz = TypeAdapter(QuizModelDict).validate_python(generated_quiz)

        except Exception as _:
            return {
                "messages": messages,
                "quiz": None,
            }

        # check if fill_in_the_blanks question has {} templates
        for question in parsed_quiz.get("questions", []):
            if question.get("type") == "multiple-choice":
                if not set(question.get("solution", [])).issubset(
                    set(question.get("options", []))
                ):
                    messages.append(
                        HumanMessage(
                            content="The previous quiz had multiple-choice questions where the solution was not exact part of the options. Please output the quiz in the correct JSON format.",
                        )
                    )
                    return {
                        "messages": messages,
                        "quiz": None,
                    }
            if question.get("type") == "fill-in-the-blank":
                question["type"] = "fill-in-the-blanks"
            if question.get("type") == "fill-in-the-blanks":
                if question.get("template", None) and "{}" not in question.get(
                    "template"
                ):

                    class PromptReturnDict(TypedDict):
                        new_template: Annotated[
                            str,
                            ...,
                            "The corrected fill-in-the-blanks question template with '{}' for the blanks.",
                        ]

                    prompt = PromptTemplate(
                        input_variables=["question_json"],
                        template="The fill-in-the-blanks question does not have any or incorrect '{{}}' in the template. Please fix it by adding exactly '{{}}' where the blank should be.\n\nExample:\nWrong: 'London is in the ____.'\nCorrected: 'London is in the {{}}.'\n\nQuestion Template:\n{question_json}",
                    )
                    chain = prompt | llm.with_structured_output(PromptReturnDict)
                    response: PromptReturnDict = await chain.ainvoke(
                        {
                            "question_json": question.get("template", ""),
                        }
                    )
                    question["template"] = response.get(
                        "new_template", question.get("template", "")
                    )

                    messages.append(
                        HumanMessage(
                            content=f"Corrected fill-in-the-blanks question template:\n{json.dumps(question, indent=2)}"
                        )
                    )

        # convert to a QuizModel
        quiz_model = QuizModel(
            id="0",  # ID will be assigned in Frontend
            title=parsed_quiz.get("title", "Quiz"),
            description=parsed_quiz.get("description", ""),
            questions=[],
            score=(0, 0),
        )
        max_score_total = 0

        for q in parsed_quiz.get("questions", []):
            question_type = q.get("type")
            if question_type == QuizType.MULTIPLE_CHOICE.value:
                from framework.api_types.quiz_models import MultipleChoiceQuestion

                options = q.get("options", [])
                correct_answer_str = q.get("correct_answer", "")
                solution_idx = 0

                # Try case-insensitive match
                for i, opt in enumerate(options):
                    opt_text = str(opt)
                    if (
                        str(opt_text).strip().lower()
                        == str(correct_answer_str).strip().lower()
                    ):
                        solution_idx = i
                        break

                question = MultipleChoiceQuestion(
                    id=q.get("id"),
                    title=q.get("title"),
                    text=q.get("text"),
                    type=QuizType.MULTIPLE_CHOICE,
                    score=(0, MAXSCORES[QuizType.MULTIPLE_CHOICE]),
                    hint=q.get("hint", ""),
                    learning_unit=q.get("learning_unit", ""),
                    answered=False,
                    options=options,
                    solution=[solution_idx],
                    answer=None,
                )
            elif question_type == QuizType.SLIDER.value:
                from framework.api_types.quiz_models import SliderQuestion

                question = SliderQuestion(
                    id=q.get("id"),
                    title=q.get("title"),
                    text=q.get("text"),
                    score=(0, MAXSCORES[QuizType.SLIDER]),
                    hint=q.get("hint", ""),
                    learning_unit=q.get("learning_unit", ""),
                    min=q.get("min", 0),
                    max=q.get("max", 10),
                    step=q.get("step", 1),
                    solution=q.get("correct_answer", 0),
                )
            elif question_type == QuizType.FREETEXT.value:
                from framework.api_types.quiz_models import TextQuestion

                question = TextQuestion(
                    id=q.get("id"),
                    title=q.get("title"),
                    text=q.get("text"),
                    score=(0, MAXSCORES[QuizType.FREETEXT]),
                    hint=q.get("hint", ""),
                    learning_unit=q.get("learning_unit", ""),
                    placeholder=q.get("placeholder", ""),
                    solution=q.get("correct_answer", ""),
                )
            elif question_type == QuizType.FILL_IN_BLANKS.value:
                from framework.api_types.quiz_models import FillInTheBlanksQuestion

                question = FillInTheBlanksQuestion(
                    id=q.get("id"),
                    title=q.get("title"),
                    text=q.get("text"),
                    score=(0, MAXSCORES[QuizType.FILL_IN_BLANKS]),
                    hint=q.get("hint", ""),
                    learning_unit=q.get("learning_unit", ""),
                    template=q.get("template", ""),
                    solution=q.get("correct_answer", []),
                )
            else:
                logger.warning(f"Unknown question type: {question_type}")
                continue  # Skip unknown question types

            max_score_total += question.score[1]
            quiz_model.questions.append(question)

        quiz_model.score = (0, max_score_total)
        
        queue = config["configurable"].get("queue")
        if queue:
            event = MessageEvent(
                timestamp=datetime.now().isoformat(),
                event="quiz_complete",
                additional_info={
                    "quiz": quiz_model,
                },
            )
            chunk = create_chunk(
                msg_id=request.id,
                request=request,
                instructions=[f"quiz_complete: {event.model_dump_json()}"],
            )
            await queue.put(chunk)

        return {
            "messages": messages,
            "quiz": quiz_model,
        }

    graph_builder = StateGraph(QuizState)
    graph_builder.add_node("agent", agent)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("verifier", verifier)
    graph_builder.add_node("json_formatter", json_formatter)
    graph_builder.add_node("json_generator", generate_json)
    graph_builder.add_node("final_verifier", final_verifier)
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges(
        "agent",
        custom_tools_condition,
        {"tools": "tools", "__end__": "verifier"},
    )
    graph_builder.add_conditional_edges(
        "verifier",
        custom_verifier_condition,
        {"try_again": "agent", "__end__": "json_formatter"},
    )
    graph_builder.add_conditional_edges(
        "json_formatter",
        custom_json_formatter_condition,
        {"generate_json": "json_generator", "__end__": "final_verifier"},
    )
    graph_builder.add_edge("json_generator", "final_verifier")
    graph_builder.add_conditional_edges(
        "final_verifier",
        custom_json_formatter_condition,
        {"generate_json": "json_generator", "__end__": END},
    )

    return graph_builder.compile()


def custom_json_formatter_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
    quiz_key: str = "quiz",
) -> Literal["generate_json", "__end__"]:
    """Check if the json formatter was successful."""
    found_quiz = None
    if isinstance(state, dict):
        found_quiz = state.get(quiz_key, None)
    elif isinstance(state, list):
        raise ValueError("State should not be a list in json formatter condition.")
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if found_quiz is not None and found_quiz != {}:
        return "__end__"
    return "generate_json"


def custom_verifier_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["tools", "__end__", "formulate_answer"]:
    """Check if the verifier wants to try again."""
    if isinstance(state, list):
        ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
        ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if "try_again" in ai_message.content.lower():
        return "try_again"
    return "__end__"


async def get_quiz_agent_prompt(request: RequestModel, db: Database, tools=None) -> str:
    """Get the prompt for the quiz agent."""
    locale = request.locale()
    learner_model = format_learner_model(request.find_store("learner_model", {}))
    agent_prompt = get_localized_langfuse_prompt(
        "competence-quiz-agent", locale, request.response_preferences
    )
    tool_list, tool_descriptions = get_tool_descriptions_from_langfuse(
        locale, [tool.name for tool in tools], request.response_preferences
    )

    learning_units_to_test = await get_learning_units_to_test(request, db)
    formatted_lus = ""
    if any(learning_units_to_test["new_since_last_quiz"]):
        new_since_last_quiz_formatted = format_learning_units(
            learning_units_to_test["new_since_last_quiz"], request.locale()
        )
        formatted_lus += f"\n\n**New learning units since last quiz:**\n{new_since_last_quiz_formatted}"
    if any(learning_units_to_test["quizzed_but_not_completed"]):
        quizzed_but_not_completed_formatted = format_learning_units(
            learning_units_to_test["quizzed_but_not_completed"], request.locale()
        )
        formatted_lus += f"\n\n**Learning units previously quizzed but not yet completed:**\n{quizzed_but_not_completed_formatted}"
    if any(learning_units_to_test["new_of_level"]):
        new_of_level_formatted = format_learning_units(
            learning_units_to_test["new_of_level"], request.locale()
        )
        formatted_lus += f"\n\n**New learning units of the current competence level:**\n{new_of_level_formatted}"

    agent_prompt_messages = agent_prompt.format_messages(
        number_of_questions=5,
        learner_model=learner_model,
        tool_descriptions=tool_descriptions,
        learning_units=formatted_lus,
    )

    sys_message = agent_prompt_messages[0]
    return sys_message


async def get_verifier_prompt(
    request: RequestModel, db: Database, quiz_lus: list[LearningUnitCombined]
) -> str:
    """Get the prompt for the quiz agent."""
    locale = request.locale()
    learner_model = format_learner_model(request.find_store("learner_model", {}))
    agent_prompt = get_localized_langfuse_prompt(
        "competence-quiz-verifier", locale, request.response_preferences
    )

    formatted_lus = format_learning_units(quiz_lus, request.locale())

    agent_prompt_messages = agent_prompt.format_messages(
        learner_model=learner_model,
        relevant_learning_units=formatted_lus,
    )

    sys_message = agent_prompt_messages[0]
    return sys_message
