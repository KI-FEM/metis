import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.responses import StreamingResponse
from langchain_core.globals import set_debug

from bots.study.agents.quiz_agent import stream_quiz_agent
from framework.api_types.ai_models import LLMPurpose

# Add src/ directory to path for module imports
sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features, ResponseGenerationData, TopicType
from bots.study.agents.lead_agent import stream_open_conversation_agent
from bots.study.chat import (
    generate_inspirations,
    open_conversation_base,
)
from bots.study.citation import setup_citation_endpoints
from bots.study.endpoints import get_topic_intro
from bots.study.helpers.helpers import (
    TOPIC_CODE,
    embeddings,
    get_llm,
    get_localized_langfuse_prompt,
    localized,
)
from bots.study.helpers.models import (
    FeedbackRequest,
    InspirationsResponse,
    PlanResponse,
)
from bots.study.quiz import (
    answer_initial_quiz,
    answer_quiz,
    complete_quiz,
    evaluate_quiz_question,
    generate_initial_quiz,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.module import Skill
from framework.api_types.quiz_models import (
    InitialQuizAnswersRecommendation,
    InitialQuizAnswersRequest,
    InitialQuizModel,
    QuizAnswersRequest,
    QuizQuestionEvaluationRequest,
    QuizQuestionEvaluationResponse,
)
from framework.api_types.request_format import (
    LearnerModelLearningUnit,
    RequestModel,
)
from framework.api_types.response_format import (
    MessageResponse,
    MetaInformation,
    Response,
    SummaryResponse,
)
from framework.api_types.topics import Topic
from framework.chains.passthrough_chain import PassthroughChain
from framework.config import get_config
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever

logger = logging.getLogger()
dev = os.environ.get("ENVIRONMENT", "development") == "development"
set_debug(dev)

# Configure logging format to include timestamp, class and method
logging.basicConfig(
    format="%(asctime)s [%(name)s] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


class StudyCompetenceBot(BaseBot):
    """Bot for assisting in learning about study competence."""

    def __init__(self):
        """Initialize the study competence bot.

        This constructor sets up the StudyCompetenceBot with its configuration,
        including localization, features, LLM clients, and color. It also initializes
        the parent BaseBot class with the appropriate parameters for study competence.

        Args:
            None
        Returns:
            None

        """
        super().__init__(
            Topic.study_competence_bot.value,
            LocalizedString("Kira", "Kira"),
            LocalizedString(
                "Find your own study strategies with your systemic AI coach.",
                (
                    "Finde eigene Lösungsstrategien fürs Studium mit deinem "
                    "systemischen KI-Coach."
                ),
            ),
            LocalizedString(
                localized(LocaleType.EN, "bot_description"),
                localized(LocaleType.DE, "bot_description"),
            ),
            embeddings,
            features=[
                Features.INSPIRATIONS,
                Features.QUIZ,
                Features.INITIAL_QUIZ,
                Features.STREAMING,
                Features.SUMMARY,
                Features.DASHBOARD,
            ],
            bot_type=TopicType.COACH,
            priority=999,
            optional=False,
            color="#b24082",
            avatar="/static/images/{theme}/kira.png",
        )

    async def get_modules(self) -> list[Skill]:
        """Get the available modules for study competence.

        This method extracts and returns a list of Skill objects representing the
        modules available to learn for the study competence topic.

        Args:
            None
        Returns:
            list[Skill]: List of Skill objects representing available modules.

        """
        db = await self.get_db()
        topic = await db.get_topic_by_code(TOPIC_CODE)
        skills = await db.get_skills(topic.idtopic)
        theme = "{theme}"
        for skill in skills:
            skill.image = f"/static/images/{theme}/{skill.code}.png"
        return skills

    async def get_retriever(self) -> SubDocRetriever:
        """Get the sub-document retriever for the study competence bot."""
        db = await self.get_db()
        vector_store = await self.get_vector_store()
        return SubDocRetriever(
            db,
            embedding=embeddings,
            vector_store=vector_store,
            llms=[], # only used for ingestion not for retrieving
        )

    async def init_chat(self, request: RequestModel) -> Response:
        """Start chat and send greeting message.

        This method initializes a chat session with the user, sending a greeting
        message. If a module is already selected, it greets the user accordingly and
        provides a button to start with the selected module. Otherwise, it prompts the
        user to select a module.

        Args:
            request (RequestModel): The incoming request containing user and
                session data.

        Returns:
            Response: The response containing greeting messages and optional buttons.

        """
        logger.info("StudyCompetenceBot: Initializing chat")

        db = await self.get_db()

        locale = request.locale()
        learner_model = await request.learner_model(db=db)

        user_memory = request.find_store("user_memory", "")
        conversation_strategy = request.find_store(
            "conversation_strategy", "No strategy available."
        )
        conversation_history = request.chat_history
        if len(conversation_history) > 0 and conversation_history[-1].content == "":
            # remove latest message if empty
            conversation_history = conversation_history[:-1]

        prompt = get_localized_langfuse_prompt(
            "competence-greeting",
            locale,
            request.response_preferences,
            chat=conversation_history,
        )
        localized_llm = await get_llm(locale, LLMPurpose.OPTIMAL)
        chain = PassthroughChain().create_chain(
            llm=localized_llm.llm(),
            prompt=prompt,
            session_id=request.find_store("chat_id", None),
            tags=["greeting"],
            use_dict_output_parser=True,
        )

        if request.streaming:
            streaming_data = ResponseGenerationData(
                chain_config={
                    "user_memory": user_memory,
                    "conversation_strategy": conversation_strategy,
                },
                created_chain=chain,
                sources={},
                llm_model=localized_llm.get_model_name(),
                storage={"learner_model": learner_model.save_learner_model()},
                metadata_information={
                    "source": "init_chat"
                }
            )
            return StreamingResponse(
                self.stream_message(request, streaming_data),
                media_type="text/event-stream",
            )
        else:
            response = await chain.ainvoke(
                {
                    "user_memory": user_memory,
                    "conversation_strategy": conversation_strategy,
                }
            )
            if isinstance(response, dict) and "answer" in response:
                resp = Response.from_message(response["answer"])
            else:
                resp = Response.from_message(response)
            resp.messages[0].meta_information = MetaInformation(source="init_chat")
            resp.storage = {"learner_model": learner_model.save_learner_model()}
            return resp

    async def chat_invoke(self, request: RequestModel) -> Response | StreamingResponse:
        """Invoke the study competence bot for a chat request.

        This method processes a chat request, handling both streaming and non-streaming
        responses. It invokes the open conversation logic and returns the appropriate
        response format, including handling of thoughts and sources if present.

        Args:
            request (RequestModel): The incoming chat request.

        Returns:
            Response | StreamingResponse: The chat response, either as a standard
                response or a streaming response.

        """
        logger.info("StudyCompetenceBot: Processing chat request")

        retriever = await self.get_retriever()
        db = await self.get_db()

        # fix learner_model if old
        _ = await request.learner_model(db=db)

        return StreamingResponse(
            stream_open_conversation_agent(request, db, retriever),
            media_type="text/event-stream",
        )
        # OLD WAY

        resp = await open_conversation_base(
            request,
            self.id,
            await self.get_db(),
            await self.get_vector_store(),
            await self.get_retriever(),
        )
        if request.streaming:
            # handle streaming response separately
            return StreamingResponse(
                self.stream_message(request, resp), media_type="text/event-stream"
            )

        # handle non-streaming response
        if isinstance(resp, Response):
            return resp
        resp: ResponseGenerationData = resp
        created_chain = resp.created_chain
        chain_config = resp.chain_config

        # invoke the LLM chain
        response = await created_chain.ainvoke(chain_config)
        if (
            isinstance(response, dict)
            and "answer" in response
            and "citations" in response
        ):
            return Response(
                messages=[
                    MessageResponse(
                        content=response["answer"],
                        meta_information=MetaInformation(
                            sources=resp.sources,
                            citations=response["citations"],
                            llm_model=resp.llm_model,
                        ),
                    )
                ]
            )
        if isinstance(response, str):
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                parsed = {"answer": response}
        message_response = MessageResponse(
            content=parsed.get("answer", response),
            meta_information=MetaInformation(
                sources=resp.sources, llm_model=resp.llm_model
            ),
        )
        if "</think>" in response:
            # thinking model
            split = response.split("</think>")
            response = split[1]
            thoughts = split[0]
            message_response.thoughts = thoughts

        # standard model
        return Response(messages=[message_response])

    async def inspirations(self, request: RequestModel) -> InspirationsResponse:
        """Get suggested questions for the user to ask.

        This method generates contextual inspirations based on the conversation history
        and relevant knowledge from the vector database.

        Args:
            request (RequestModel): The incoming request containing locale and selected
                module.

        Returns:
            InspirationsResponse: The response containing generated questions.

        """
        logger.info("StudyCompetenceBot: Generating contextual inspirations")
        # Generate inspirations using conversation context
        generated_questions = await generate_inspirations(
            request,
            self.id,
            await self.get_db(),
            await self.get_retriever(),
        )
        return InspirationsResponse(messages=generated_questions)

    async def quiz(self, request: RequestModel) -> StreamingResponse:
        """Take a test to evaluate the learning progress.

        This method generates a quiz for the user based on the selected module, skill
        level, and learning type. It retrieves relevant documents, builds a prompt, and
        invokes the LLM to generate quiz questions. Retries up to 3 times if the
        response is not valid JSON.

        Args:
            request (RequestModel): The incoming request containing language,
                learning type, selected module, and chat history.

        Returns:
            QuizModel: The generated quiz model with questions.

        """
        logger.info("StudyCompetenceBot: Generating quiz")
        db = await study_competence_bot.get_db()
        return StreamingResponse(
            stream_quiz_agent(request, db),
            media_type="text/event-stream",
        )

    async def answer_quiz(self, request: QuizAnswersRequest) -> Response:
        """Submit the answers to the test and get feedback.

        This method processes the user's quiz answers, formats them, and sends them to
        the LLM for feedback. It handles retries and validation of the feedback
        response, returning a Response with the feedback message.

        Args:
            request (QuizAnswersRequest): The request containing answers, questions,
                and chat history.

        Returns:
            Response: The response containing feedback on the quiz answers.

        """
        logger.info("StudyCompetenceBot: Processing quiz answers")
        return await answer_quiz(request, study_competence_bot.id)

    async def evaluate_quiz_question(
        self,
        request: QuizQuestionEvaluationRequest,
    ) -> QuizQuestionEvaluationResponse:
        """Evaluate a single quiz question answer.

        This method evaluates the user's answer to a single quiz question and returns
        a score, correctness status, solution, and feedback.

        Args:
            request (QuizQuestionEvaluationRequest): The request containing the question
                and user's answer.

        Returns:
            QuizQuestionEvaluationResponse: The evaluation result with score,
                correctness, solution, and feedback.

        """
        logger.info("StudyCompetenceBot: Evaluating quiz question")
        return await evaluate_quiz_question(request, await self.get_db())

    async def complete_quiz(self, request):
        """Complete the quiz and provide a summary of results."""
        return await complete_quiz(request, await self.get_db())

    async def initial_quiz(self, request: RequestModel) -> InitialQuizModel:
        """Generate an initial quiz to assess the user's current knowledge level.

        This method creates an initial assessment quiz for the user based on the
        selected module and learning context. It helps determine the user's baseline
        knowledge before starting the learning journey.

        Args:
            request (RequestModel): The incoming request containing language,
                learning type, selected module, and chat history.

        Returns:
            InitialQuizModel:
                The generated initial quiz model with assessment questions.

        """
        logger.info("StudyCompetenceBot: Generating initial quiz")
        db = await study_competence_bot.get_db()
        retriever = await study_competence_bot.get_retriever()
        return await generate_initial_quiz(
            request, db, retriever, study_competence_bot.id
        )

    async def answer_initial_quiz(
        self, request: InitialQuizAnswersRequest
    ) -> InitialQuizAnswersRecommendation:
        """Submit the answers to the initial quiz and get feedback.

        This method processes the user's initial_quiz answers, checks their competence
        level and if the users level should change.

        Args:
            request (InitialQuizAnswersRequest):
                The request containing the correct question IDs.

        Returns:
            InitialQuizAnswersRecommendation:
                The response containing feedback on the initial quiz answers.

        """
        logger.info("StudyCompetenceBot: Processing initial quiz answers")
        db = await study_competence_bot.get_db()
        return await answer_initial_quiz(request, db, study_competence_bot.id)

    async def feedback(self, request: FeedbackRequest) -> Response:
        """Ask the user to provide feedback on the bot's performance.

        This method processes user feedback on the bot's performance, returning a
        localized response based on the feedback rating.

        Args:
            request (FeedbackRequest): The feedback request containing language and
            feedback rating.

        Returns:
            Response: The response message acknowledging the feedback.

        """
        # TODO: what to do with feedback?
        # feedback = \ request.feedback.comment
        locale = LocaleType(request.language)
        learning_type_fit = request.feedback.learning_type_rating
        logger.info("StudyCompetenceBot: Received feedback")

        # simply acknowledge the feedback
        response = ""
        if learning_type_fit < 5:
            response = localized(locale, "feedback_low_fit")
        else:
            response = localized(locale, "feedback_high_fit")
        await asyncio.sleep(0.001)
        return Response.from_message(response)

    async def plan_session(self, request: RequestModel) -> PlanResponse:
        """Plan the next study session for the user.

        This method recommends topics and a date for the user's next study session based
        on their current skill, level, and learning goals. It ensures recommended topics
        exist and fills in with random topics if needed. Recommended topics are returned
        from the headers of all available modules.

        Args:
            request (RequestModel): The incoming request containing learning type,
            locale, selected module, and skill level.

        Returns:
            PlanResponse: The response containing recommended topics and date.

        """
        locale = request.locale()
        competence_level_id = request.find_store("skill_level")
        selected_competence = request.find_store("selected_competence", "")
        learner_model: list[LearnerModelLearningUnit] = request.find_store(
            "learner_model", []
        )
        completed_luids = [lu.id for lu in learner_model if lu.completed]

        # get all concepts not yet completed
        db = await self.get_db()
        competence = await db.get_competence_by_code(selected_competence)
        concepts = await db.get_concepts_not_completed_yet(
            competence.idcompetence, competence_level_id, completed_luids, locale
        )
        topics = [concept.name for concept in concepts]

        # plan a date for the next session, current implementation: 7 days from now
        planned_date = (datetime.now() + timedelta(days=7)).date().isoformat()

        return PlanResponse(recommended_topics=topics, recommended_date=planned_date)

    async def summarize(self, request: RequestModel) -> SummaryResponse:
        """Summarize the chat history asynchronously.

        This endpoint is called asynchronously by the frontend to summarize long
        conversations without blocking the main chat interaction.
        Summaries are sent and saved in the frontend and used
        instead of the prior chat history.

        Args:
            request (RequestModel): The incoming request containing chat history and
            locale.

        Returns:
            SummaryResponse: The response containing the summary and message retention
            info.

        """
        logger.info("StudyCompetenceBot: Summarizing chat")
        summary_result = await self.summarize_chat(
            request, llm_client=(await get_llm(request.locale()))
        )
        
        keep_last_msgs_until = await get_config("KEEP_LAST_MESSAGES_UNTIL")
        if summary_result.summary:
            return SummaryResponse(
                summary=summary_result.summary,
                keep_last_messages_until=int(keep_last_msgs_until),
            )
        return SummaryResponse(summary="", keep_last_messages_until=0)


study_competence_bot = StudyCompetenceBot()
post = study_competence_bot.post  # used to define custom POST endpoints

# additional module endpoints
setup_citation_endpoints(post)


@post("/select_competence")
async def select_competence(request: RequestModel) -> Response:
    """Select a competence to learn about and give an introduction into the topic."""
    return await get_topic_intro(
        request,
        study_competence_bot.id,
        await study_competence_bot.get_db(),
        await study_competence_bot.get_retriever(),
    )
