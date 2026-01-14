import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict

from langchain_core.runnables import RunnablePassthrough
from pydantic import ValidationError

# Add src/ directory to path for module imports
sys.path.append(str(Path(__file__).parent.parent))
from bots.study.agents.quiz_agent import MAXSCORES
from bots.study.helpers.helpers import (
    format_learning_units,
    get_llm,
    get_localized_langfuse_prompt,
    localized,
)
from bots.study.helpers.models import (
    QuizFeedbackResponseDict,
    QuizModelDict,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.quiz_models import (
    FillInTheBlanksQuestion,
    InitialQuizAnswersRecommendation,
    InitialQuizAnswersRequest,
    InitialQuizModel,
    MultipleChoiceQuestion,
    QuizAnswersRequest,
    QuizCompletionRequest,
    QuizCompletionResponse,
    QuizModel,
    QuizQuestionEvaluationRequest,
    QuizQuestionEvaluationResponse,
    SliderQuestion,
    TextQuestion,
)
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
from framework.db.database import Database
from framework.llm.lite_llm import LiteLLM
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever

logger = logging.getLogger()
CORRECT_ANSWERS_BEFORE_COMPLETION = 3  # TODO arbitrary threshold for completion


async def randomize_quiz_option_ids(quiz_model: QuizModel) -> QuizModel:
    """Randomize the positions of quiz options to scramble their order."""
    # shuffle the questions
    random.shuffle(quiz_model.questions)

    for question in quiz_model.questions:
        if question.options:
            # Shuffle the actual list of options
            random.shuffle(question.options)

    return quiz_model


async def evaluate_choice(
    user_answer: List[int], question: MultipleChoiceQuestion, max_score: int, locale
):
    """Evaluate a multiple-choice or single-choice question."""
    # Direct comparison for multiple choice
    correct_answer = getattr(question, "solution", [])
    is_correct = set(user_answer) == set(correct_answer)
    score = max_score if is_correct else 0

    if is_correct:
        feedback = localized(locale, "quiz_correct") if locale else "Correct!"
    else:
        feedback = (
            localized(locale, "quiz_incorrect")
            if locale
            else "Incorrect. Please review the material."
        )

    return QuizQuestionEvaluationResponse(
        score=score,
        max_score=max_score,
        is_correct=is_correct,
        solution=correct_answer,
        feedback=feedback,
    )


async def evaluate_slider(
    user_answer: int, question: SliderQuestion, max_score, locale
):
    """Evaluate a slider question."""
    # Direct comparison for slider (with some tolerance)
    correct_answer = getattr(question, "solution", 0)
    try:
        correct_value = float(correct_answer)
        user_value = float(user_answer)

        # Allow a tolerance of ±1
        is_correct = abs(user_value - correct_value) <= 1
        score = max_score if is_correct else 0

        if is_correct:
            feedback = localized(locale, "quiz_correct") if locale else "Good estimate!"
        else:
            feedback = (
                localized(locale, "quiz_slider_hint")
                if locale
                else f"The correct answer is around {correct_value}."
            )

        return QuizQuestionEvaluationResponse(
            score=score,
            max_score=max_score,
            is_correct=is_correct,
            solution=correct_answer,
            feedback=feedback,
        )
    except (ValueError, IndexError):
        # Fallback if parsing fails
        return QuizQuestionEvaluationResponse(
            score=0,
            max_score=max_score,
            is_correct=False,
            solution=correct_answer,
            feedback="Unable to evaluate answer.",
        )


async def evaluate_fill_in_blanks(
    user_answer: List[str],
    question: FillInTheBlanksQuestion,
    max_score,
    locale,
    db: Database,
):
    """Evaluate a fill-in-the-blanks question using an LLM."""
    correct_blanks = getattr(question, "solution", [])
    user_blanks = user_answer if isinstance(user_answer, list) else [user_answer]

    # if the user answered exactly correctly, then don't ask the llm
    if len(user_blanks) == len(correct_blanks) and all(
        str(ub).strip().lower() == str(cb).strip().lower()
        for ub, cb in zip(user_blanks, correct_blanks)
    ):
        return QuizQuestionEvaluationResponse(
            score=max_score,
            max_score=max_score,
            is_correct=True,
            solution=correct_blanks,
            feedback=localized(locale, "quiz_correct") if locale else "Correct!",
        )

    llm = await get_llm(locale)
    prompt = get_localized_langfuse_prompt(
        "competence-quiz-evaluate-blanks",
        locale,
        None,
    )

    class PromptReturnDict(TypedDict):
        reasoning: str
        is_correct: bool
        score: int
        feedback: str

    chain = prompt | llm.llm_chatopenai().with_structured_output(PromptReturnDict)

    retrieved_lu = await db.get_learning_units_joined_by_code(
        [question.learning_unit], locale
    )

    solution = ", ".join(str(b) for b in correct_blanks)

    answer = await chain.ainvoke(
        {
            "question": question.template,
            "user_answers": ", ".join(str(b) for b in user_blanks),
            "correct_answers": solution,
            "max_score": max_score,
            "learning_unit": format_learning_units(
                [retrieved_lu[0]],
                locale,
            )
            if len(retrieved_lu) > 0
            else "N/A",
        }
    )

    return QuizQuestionEvaluationResponse(
        score=answer.get("score"),
        max_score=max_score,
        is_correct=answer.get("is_correct"),
        solution=correct_blanks,
        feedback=answer.get("feedback"),
    )


async def evaluate_free_text(
    user_answer, question: TextQuestion, max_score, locale, db: Database
):
    """Evaluate a free-text question using an LLM."""
    # Mock LLM evaluation for free-text
    # TODO: Implement actual LLM evaluation
    correct_answer = getattr(question, "solution", "")

    llm = await get_llm(locale)
    prompt = get_localized_langfuse_prompt(
        "competence-quiz-evaluate-free-text",
        locale,
        None,
    )

    class PromptReturnDict(TypedDict):
        reasoning: str
        score: int
        is_correct: bool
        feedback: str

    chain = prompt | llm.llm_chatopenai().with_structured_output(PromptReturnDict)

    retrieved_lu = await db.get_learning_units_joined_by_code(
        [question.learning_unit], locale
    )

    answer = await chain.ainvoke(
        {
            "question": question.text,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "max_score": max_score,
            "learning_unit": format_learning_units(
                [retrieved_lu[0]],
                locale,
            )
            if len(retrieved_lu) > 0
            else "N/A",
        }
    )

    return QuizQuestionEvaluationResponse(
        score=answer.get("score"),
        max_score=max_score,
        is_correct=answer.get("is_correct"),
        solution=correct_answer,
        feedback=answer.get("feedback"),
    )


async def evaluate_quiz_question(
    request: QuizQuestionEvaluationRequest, db: Database
) -> QuizQuestionEvaluationResponse:
    """Evaluate a single quiz question answer.

    This method evaluates the user's answer to a single quiz question and returns
    a score, correctness status, solution, and feedback.

    Args:
        request (QuizQuestionEvaluationRequest): The request containing the question
            and user's answer.
        db (Database): The database instance for any necessary lookups.

    Returns:
        QuizQuestionEvaluationResponse: The evaluation result with score, correctness,
            solution, and feedback.

    """
    question = request.question
    user_answer = request.user_answer
    locale = request.locale()

    # Determine max score based on question type

    max_score = MAXSCORES.get(question.type, 1)

    # Evaluate based on question type
    if question.type == "multiple-choice" or question.type == "single-choice":
        return await evaluate_choice(user_answer, question, max_score, locale)

    elif question.type == "slider":
        return await evaluate_slider(user_answer, question, max_score, locale)

    elif question.type == "fill-in-the-blanks":
        return await evaluate_fill_in_blanks(
            user_answer, question, max_score, locale, db
        )

    elif question.type == "free-text":
        return await evaluate_free_text(user_answer, question, max_score, locale, db)

    else:
        # Unknown question type
        return QuizQuestionEvaluationResponse(
            score=0,
            max_score=max_score,
            is_correct=False,
            solution="Unknown question type",
            feedback="Unable to evaluate this question type.",
        )


async def complete_quiz(
    request: QuizCompletionRequest, db: Database
) -> QuizCompletionResponse:
    """Evaluate the quiz and update the learner model."""
    learner_model = await request.learner_model(db=db)
    events = []
    quiz = request.quiz
    for question in quiz.questions:
        if not question.answered:
            logger.warning(f"Question {question.id} was not answered.")
            continue  # Skip unanswered questions

        lu_code = question.learning_unit
        correct = question.score[0] > 0
        # Find or create the learning unit entry in the learner model
        lu_entry = (
            learner_model.learning_units[lu_code]
            if lu_code in learner_model.learning_units
            else None
        )

        if not lu_entry:
            logger.error(f"Learning unit {lu_code} not found in learner model.")
            continue  # Skip if learning unit not found

        # Update existing entry
        lu_entry.times_quizzed += 1
        lu_entry.last_quizzed = datetime.now().isoformat()
        events.append(
            {
                "type": "learning_unit_increased_times_quizzed",
                "learning_unit": lu_code,
            }
        )
        if not correct:
            continue  # If not correct, we don't need to do anything else

        lu_entry.times_correct += 1
        events.append(
            {
                "type": "learning_unit_increased_times_correct",
                "learning_unit": lu_code,
                "learning_unit_name": lu_entry.name,
            }
        )
        if lu_entry.times_correct >= CORRECT_ANSWERS_BEFORE_COMPLETION:
            lu_entry.completed = True
            events.append(
                {
                    "type": "learning_unit_completed",
                    "learning_unit": lu_code,
                    "learning_unit_name": lu_entry.name,
                }
            )

    # Build the messaage to return
    full_message = set()
    for event in events:
        if (
            event["type"] == "learning_unit_increased_times_quizzed"
            or event["type"] == "learning_unit_increased_times_correct"
        ):
            full_message.add(localized(request.locale(), "quiz_response_updated"))
        elif event["type"] == "learning_unit_completed":
            full_message.add(
                localized(
                    request.locale(),
                    "quiz_response_learning_unit_completed",
                ).format(
                    unit=event["learning_unit_name"].get(request.locale().value, "de")
                )
            )
        elif event["type"] == "concept_increased_competence_level":
            full_message.add(
                localized(
                    request.locale(),
                    "quiz_response_concept_increased_competence_level",
                ).format(
                    concept=event["concept"],
                    level=int(event["new_level"]),
                )
            )

    return_message = MessageResponse(
        content="\n".join(full_message) if full_message else "Quiz completed.",
    )
    new_storage = {
        **request.storage,
        "learner_model": learner_model.save_learner_model(),
    }

    return QuizCompletionResponse(
        messages=[return_message], storage=new_storage, events=events
    )


def get_timestamp() -> str:
    """Get the current timestamp as a string."""
    return datetime.now().isoformat()


async def answer_quiz(request: QuizAnswersRequest, bot_id):
    """Generate a response for the quiz answers."""
    locale = request.locale()
    answers = request.answers
    messages = request.chat_history
    if not messages:
        logger.error("No chat history found.")
        return Response(
            messages=[MessageResponse(content="Please start a conversation first.")]
        )
    questions = request.questions
    prompt = get_localized_langfuse_prompt(
        "competence-quiz-conclusion",
        locale,
        request.response_preferences,
        chat=messages,
    )

    # calculate which learning units where correctly answered and which were quizzed
    correct_learning_units = []
    quizzed_learning_units = []

    for answer in answers:
        selected_answers = answer.selected_options_ids
        question_id = answer.question_id
        question = [question for question in questions if question.id == question_id]
        if question:
            quizzed_learning_units.append(question[0].learning_unit)
            correct_option = [
                option for option in question[0].options if option.correct
            ]
            if correct_option and correct_option[0].id in selected_answers:
                correct_learning_units.append(question[0].learning_unit)

    # update the learner model
    learner_model: list[LearnerModelLearningUnit] = request.storage.get(
        "learner_model", []
    )
    learner_model_dict = {lu["id"]: lu for lu in learner_model}
    for lu in quizzed_learning_units:
        if lu in learner_model_dict:
            # update existing entry
            entry = learner_model_dict[lu]
            entry["times_quizzed"] += 1
            entry["last_quizzed"] = get_timestamp()
            if lu in correct_learning_units:
                entry["times_correct"] += 1
                if entry["times_correct"] >= CORRECT_ANSWERS_BEFORE_COMPLETION:
                    entry["completed"] = True
        else:
            # add new entry
            learner_model_dict[lu] = LearnerModelLearningUnit(
                id=lu,
                code="bla",
                name={"en": "New Learning Unit", "de": "Neue Lerneinheit"},  # TODO
                times_seen=0,
                last_seen=None,
                times_quizzed=1,
                last_quizzed=get_timestamp(),
                completed=False,
            )

    updated_learner_model = list(learner_model_dict.values())

    # Idea: Let LLM verify if learning goal is really achieved by this answer,
    # because the generated question could be the same topic,
    # but less difficult than the example task,
    # thus it would be easy to achieve the learning goal

    def format_answers(answers: list[int]) -> str:
        """Format the list of selected options into LLM-interpretable format."""
        if len(answers) == 0:
            return "No answer selected."
        if len(answers) == 1:
            return answers[0]
        return ", ".join(answers)

    answers_formatted = "\n".join(
        (
            f"Question #{answer.question_id}: "
            f"{format_answers(answer.selected_options_ids)}"
        )
        for answer in answers
    )
    questions_formatted = "\n".join(
        question.model_dump_json() for question in questions
    )

    # create the chain config
    chain_config = {
        "questions": questions_formatted,
        "answers": answers_formatted,
    }

    # create the LLM object
    localized_llm = await get_llm(locale, request.llm_purpose)
    # set the output format to the quiz model
    structured_llm = localized_llm.llm_chatopenai().with_structured_output(
        QuizFeedbackResponseDict
    )

    # build a chain with the structured_llm
    created_chain = (prompt | structured_llm).with_config(
        callbacks=[BaseChain.get_langfuse_callback()],
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["quiz", bot_id],
        },
    )

    response: QuizFeedbackResponseDict = await created_chain.ainvoke(chain_config)
    user_feedback = ""

    if isinstance(response, dict) and "user_feedback" in response:
        user_feedback = response["user_feedback"]
    elif isinstance(response, str):
        try:
            parsed_response = json.loads(response.strip())
            user_feedback = parsed_response.get("user_feedback", "")
        except json.JSONDecodeError:
            logger.error("Failed to parse quiz feedback response as JSON.")
            user_feedback = "Failed to parse feedback response."

    return Response(
        messages=[
            MessageResponse(
                content=localized(locale, "quiz_submitted_message"),
                type=MessageType.USER,
            ),
            MessageResponse(
                content=user_feedback,
                type=MessageType.ASSISTANT,
                meta_information=MetaInformation(
                    llm_model=localized_llm.get_model_name()
                ),
            ),
        ],
        storage={
            "learner_model": updated_learner_model  # update learner model store
        },
    )


async def generate_initial_quiz(
    request: RequestModel, db: Database, retriever: SubDocRetriever, bot_id
):
    """Generate a quiz for the study competence bot to check pre-existing knowledge."""
    locale = request.locale()
    response_preferences = request.response_preferences
    selected_competence_code = request.find_store("selected_competence", "")
    selected_level_id = int(request.find_store("skill_level") or "1")
    selected_level_ids = list(
        {
            max(1, selected_level_id - 1),
            selected_level_id,
            min(4, selected_level_id + 1),
        }
    )

    localized_llm: LiteLLM = await get_llm(locale)

    cur_competence = await db.get_competence_translated_by_code(
        selected_competence_code, locale
    )

    # Separate learning units by level
    learning_units_below = []
    learning_units_at_level = []
    learning_units_above = []

    for level_id in selected_level_ids:
        level_learning_units = await db.get_learning_units_for_competence_and_level(
            cur_competence.idcompetence, level_id, locale
        )

        # Determine the limit based on whether this is the selected level
        limit = (
            3
            if level_id == selected_level_id
            else (3 if len(selected_level_ids) == 2 else 2)
        )

        # Randomly select learning units up to the limit
        if len(level_learning_units) > limit:
            selected_units = random.sample(level_learning_units, limit)
        else:
            selected_units = level_learning_units

        # Categorize by level
        if level_id < selected_level_id:
            learning_units_below = selected_units
        elif level_id == selected_level_id:
            learning_units_at_level = selected_units
        else:  # level_id > selected_level_id
            learning_units_above = selected_units

    selected_level = await db.get_competence_level_translated(selected_level_id, locale)

    if (
        len(learning_units_at_level) == 0
        and len(learning_units_below) == 0
        and len(learning_units_above) == 0
    ):
        logger.error("No available learning units found to test")
        return InitialQuizModel(
            title="ERROR",
            description="Learning units not found.",
            questions=[],
            quiz_questions_asked_per_level=(0, 0, 0),
        )

    # Format learning units for each level
    learning_goals_below_level = (
        format_learning_units(learning_units_below, request.locale())
        if learning_units_below
        else []
    )
    learning_goals_at_level = format_learning_units(
        learning_units_at_level, request.locale()
    )
    learning_goals_above_level = (
        format_learning_units(learning_units_above, request.locale())
        if learning_units_above
        else []
    )

    custom_learning_goals = request.find_store("custom_learning_goals", [])

    # get the documents for the quiz
    # TODO: Use similar appraoch to MultiQueryRetriever to generate retrieval query
    query = get_localized_langfuse_prompt(
        "competence-quiz-retrieval",
        locale,
        response_preferences,
        requested_llm=localized_llm,
        prompt_type="text",
    ).format(topic=cur_competence.name)
    docs_and_scores = await retriever.retrieve(
        query,
        competence_id=cur_competence.idcompetence,
    )
    docs = await retriever.rerank(query, [doc for doc, _ in docs_and_scores])
    docs = docs[:5]

    # create the chain config from gathered information
    chain_config = {  # TODO: Needs to be adapted for a new prompt
        "context": docs,
        "number_of_questions": (
            len(learning_units_below)
            + len(learning_units_at_level)
            + len(learning_units_above)
        ),
        "current_level": selected_level.name,
        "learning_goals_at_level": learning_goals_at_level,
        "learning_goals_below_level": learning_goals_below_level,
        "learning_goals_above_level": learning_goals_above_level,
        "custom_learning_goals": custom_learning_goals,
    }

    # set the output format to the quiz model
    structured_llm = localized_llm.llm_chatopenai().with_structured_output(
        QuizModelDict
    )

    # build a custom chain with the structured_llm
    created_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: "\n\n".join(doc.page_content for doc in x["context"]))
        )
        | get_localized_langfuse_prompt(
            "competence-initial-quiz",  # TODO: create a new prompt
            LocaleType.EN,
            response_preferences,
            chat=request.chat_history,
            requested_llm=localized_llm,
        )
        | structured_llm
    ).with_config(
        callbacks=[BaseChain.get_langfuse_callback()],
        metadata={
            "langfuse_session_id": request.find_store(
                "unique_id", request.find_store("chat_id", None)
            ),
            "langfuse_tags": ["quiz", bot_id],
        },
    )

    # generate the quiz
    response = await created_chain.ainvoke(chain_config)
    quiz_questions_asked_per_level = (
        len(learning_units_below),
        len(learning_units_at_level),
        len(learning_units_above),
    )

    # parse the response, either it is a Dict or a JSON string
    try:
        return_model = None
        if isinstance(response, dict) and "questions" in response:
            return_model = InitialQuizModel(
                id=response.get("id", "0"),
                title=response.get("title", ""),
                description=response.get("description", ""),
                questions=response.get("questions", []),
                score=response.get("score", (0, 0)),
                quiz_questions_asked_per_level=quiz_questions_asked_per_level,
            )
        elif isinstance(response, str):
            try:
                parsed_response = json.loads(response.strip())
                return_model = InitialQuizModel(
                    id=parsed_response.get("id", "0"),
                    title=parsed_response.get("title", ""),
                    description=parsed_response.get("description", ""),
                    questions=parsed_response.get("questions", []),
                    score=parsed_response.get("score", (0, 0)),
                    quiz_questions_asked_per_level=quiz_questions_asked_per_level,
                )
            except json.JSONDecodeError:
                logger.error("Failed to parse quiz response as JSON.")
                return_model = InitialQuizModel(
                    id="0",
                    title="Quiz",
                    description="Failed to parse quiz response.",
                    questions=[],
                    score=(0, 0),
                    quiz_questions_asked_per_level=quiz_questions_asked_per_level,
                )
    except ValidationError as e:
        logger.error(f"Validation error while parsing quiz model: {e}")
        return_model = InitialQuizModel(
            title="Quiz",
            description="Failed to parse quiz response.",
            questions=[],
            quiz_questions_asked_per_level=quiz_questions_asked_per_level,
        )

    # Randomize option IDs before returning
    if return_model:
        return_model = await randomize_quiz_option_ids(return_model)

    return return_model


async def answer_initial_quiz(request: InitialQuizAnswersRequest, db, bot_id):
    """Determine if the user should change their skill level."""
    selected_level_id = int(request.find_store("skill_level") or "1")
    locale = request.locale()

    # Get learning units for the correctly answered questions
    correct_lus = await db.get_learning_units_joined(
        request.correct_question_ids, locale
    )

    questions_asked_per_level = request.questions_asked_per_level

    # Sort by competence level for analysis
    correct_lus = sorted(correct_lus, key=lambda x: x.idcompetencelevel)

    # Categorize correct answers by level relative to selected level
    correct_below = [
        lu for lu in correct_lus if lu.idcompetencelevel < selected_level_id
    ]
    correct_at_level = [
        lu for lu in correct_lus if lu.idcompetencelevel == selected_level_id
    ]
    correct_above = [
        lu for lu in correct_lus if lu.idcompetencelevel > selected_level_id
    ]

    # Calculate performance metrics
    total_below = len(correct_below)
    total_at_level = len(correct_at_level)
    total_above = len(correct_above)

    # Extract questions asked per level from tuple (below, at_level, above)
    questions_below, questions_at_level, questions_above = questions_asked_per_level

    # Calculate performance ratios (percentage of correct answers per level)
    ratio_below = total_below / questions_below if questions_below > 0 else 0
    ratio_at_level = (
        total_at_level / questions_at_level if questions_at_level > 0 else 0
    )
    ratio_above = total_above / questions_above if questions_above > 0 else 0

    # Algorithm to determine recommended level change
    recommended_level_change = 0

    # Evaluation logic based on performance ratios and patterns
    if ratio_above >= 0.5 and ratio_at_level >= 0.66:
        # User answered at least 50% of questions above their level
        # AND 67%+ at their level
        # Suggest moving up one level
        recommended_level_change = 1

    if (ratio_below >= 0.66 or questions_below == 0) and ratio_at_level == 1:
        # User answered at least 67% of questions below their level
        # AND 100% at their level
        # Suggest moving up one level
        recommended_level_change = 1

    elif ratio_below < 0.5 and questions_below > 0 and ratio_at_level < 0.34:
        # User answered less than 34% at their level AND struggled with lower levels
        # (or no lower level questions)
        # Suggest moving down one level
        recommended_level_change = -1

    elif ratio_below <= 0.5 and questions_below > 0 and ratio_at_level == 0:
        # User struggled at their level AND didn't succeed at lower levels
        # Suggest moving down one level
        recommended_level_change = -1

    else:
        # Default case: performance is adequate for current level
        recommended_level_change = 0

    return InitialQuizAnswersRecommendation(
        quiz_performance_below=total_below,
        quiz_performance_at_level=total_at_level,
        quiz_performance_above=total_above,
        quiz_recommended_change=recommended_level_change,
    )
