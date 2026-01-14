import logging
import sys
from pathlib import Path

from langchain_core.runnables import RunnableSerializable
from langchain_core.vectorstores import VectorStore
from langfuse import get_client

sys.path.append(str(Path(__file__).parent.parent))
from bots.base_bot import BaseBot, Features, Module
from bots.citation.structure import structure
from bots.study.helpers.helpers import get_llm
from framework.api_types.ai_models import LLMPurpose
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.request_format import Message, RequestModel
from framework.api_types.response_format import (
    Button,
    ButtonCallback,
    MessageResponse,
    MetaInformation,
    Response,
    Source,
    TitleResponse,
)
from framework.api_types.response_preferences import (
    ResponsePreferences,
    fill_response_preferences,
)
from framework.api_types.topics import Topic
from framework.chains import RetrievalChain
from framework.chains.passthrough_chain import PassthroughChain
from framework.db.database import Database
from framework.rag.embeddings.lite_llm_embedding import LiteLLMEmbedding
from framework.rag.vector_dbs.faiss import FAISSVectorDB

logger = logging.getLogger()

# Configure logging format to include timestamp, class and method
logging.basicConfig(
    format="%(asctime)s [%(name)s] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

STRUCTURE_ID = "scientific_writing"
STRUCTURE_ID = "scientific_writing"
embeddings = LiteLLMEmbedding()
chain = RetrievalChain()
langfuse = get_client()
langfuse = get_client()


class CitationBot(BaseBot):
    """Bot for teaching about scientific writing."""

    def __init__(self) -> None:
        """Initialize the citation bot."""
        super().__init__(
            Topic.citation_bot.value,
            LocalizedString("Scientific Writing", "Wissenschaftliches Schreiben"),
            LocalizedString(
                "Learn how to write scientific papers",
                "Lerne wissenschaftliche Arbeiten zu schreiben",
            ),
            LocalizedString(
                "This chatbot is your personal coach for scientific writing"
                " No matter if you're just getting started or"
                " already deep into the writing process:"
                " he supports you with questions, feedback, and structure."
                " Instead of providing knowledge, he guides you like a coach."
                "🇺🇸 Currently available in English only.",
                "Dieser Chatbot ist dein persönlicher Coach"
                " für wissenschaftliches Schreiben."
                " Egal, ob du gerade erst beginnst oder mitten"
                " im Schreibprozess steckst:"
                " er unterstützt dich mit Fragen, Feedback und Struktur. Statt Wissen"
                " vorzugeben, begleitet er dich im Sinne eines Coaches.\n\n"
                "🇺🇸 Aktuell nur auf Englisch verfügbar.",
            ),
            embeddings,
            features=[Features.TITLE, Features.SCIENTIFIC_PAPER_CONTEXT],
            color="#ea4d79",
        )
        self.vector_store = None
        self.db = Database()
        self.vector_store = None
        self.db = Database()

    def get_modules(self) -> list[Module]:
        """Get the modules of the bot."""
        topics = structure.get("topics", [])
        for topic in topics:
            if topic["name"] == "Scientific work":
                modules = topic.get("modules", [])
                module_names = [
                    Module(
                        id=i,
                        code=module["name"],
                        title={
                            LocaleType.DE: self._pretty_name(module["name"]),
                            LocaleType.EN: self._pretty_name(module["name"]),
                        },
                    )
                    for i, module in enumerate(modules)
                ]
                return module_names
        return []

    async def init_chat(self, request: RequestModel) -> Response:
        """Start the chat with the new structured guideline."""
        logger.info("CitationBot: Initializing chat with new guideline")

        # Start with the new guideline
        return Response(
            messages=[
                MessageResponse(
                    content=(
                        "Hi! I'm your writing coach –"
                        " here to support you, not to judge. "
                        "Writing can be messy and hard, and that's totally okay."
                        "Let's take the next step together.\n\n"
                        "First, where are you today with your writing?"
                    ),
                    meta_information=MetaInformation(source="init_chat"),
                    buttons=[
                        Button(
                            chat_message="I'm just getting started",
                            label="I'm just getting started",
                            callback=ButtonCallback(
                                endpoint="writing_status",
                                data={"status": "getting_started"},
                            ),
                        ),
                        Button(
                            chat_message="I'm stuck somewhere",
                            label="I'm stuck somewhere",
                            callback=ButtonCallback(
                                endpoint="writing_status", data={"status": "stuck"}
                            ),
                        ),
                        Button(
                            chat_message="I have something written, but need feedback",
                            label="I have something written, but need feedback",
                            callback=ButtonCallback(
                                endpoint="writing_status",
                                data={"status": "need_feedback"},
                            ),
                        ),
                        Button(
                            chat_message="I just need motivation",
                            label="I just need motivation",
                            callback=ButtonCallback(
                                endpoint="writing_status",
                                data={"status": "need_motivation"},
                            ),
                        ),
                    ],
                )
            ]
        )

    async def chat_invoke(self, request: RequestModel) -> Response:
        """Invoke the citation bot."""
        messages = request.chat_history
        response_preferences = request.response_preferences
        last_message = messages[-1].content
        logger.info("CitationBot: Processing chat request")

        vector_db = await self.get_vector_store()
        db = await self.get_db()
        topic = await db.get_topic_by_code(STRUCTURE_ID)
        created_chain = await update_chain(
            response_preferences,
            request.locale(),
            messages,
            request.find_store("chat_id"),
            request.llm_purpose,
            request.storage,
        )
        db = await self.get_db()

        # Add citation bot context to chain config if available
        chain_config = {
            "context": await vector_db.asimilarity_search(
                last_message, topic_id=topic.idtopic
            ),
        }

        # Add citation bot context variables if available in storage
        if request.storage:
            citation_context = {}
            if "thesis_title" in request.storage:
                citation_context["thesis_title"] = request.storage["thesis_title"]
            if "thesis_task" in request.storage:
                citation_context["thesis_task"] = request.storage["thesis_task"]
            if "thesis_deadlines" in request.storage:
                citation_context["thesis_deadlines"] = request.storage[
                    "thesis_deadlines"
                ]
            if "thesis_information" in request.storage:
                citation_context["thesis_information"] = request.storage[
                    "thesis_information"
                ]

            if citation_context:
                chain_config.update(citation_context)

        llm_client = await get_llm(request.locale())
        response = await created_chain.ainvoke(chain_config)
        message_response = await self.parse_response_content(response)
        message_response.meta_information = MetaInformation(
            sources={
                i: Source.from_document(doc)
                for i, doc in enumerate(chain_config["context"])
            },
            llm_model=llm_client.get_model_name(),
        )
        return Response(messages=[message_response])

    async def update_title(self, request: RequestModel) -> TitleResponse:
        """Generate the title for a chat/conversation."""
        logger.info("CitationBot: Generating title")
        messages = request.chat_history
        messages_for_prompt = messages[-2:] if len(messages) > 1 else messages
        llm_client = await get_llm(request.locale())
        prompt = llm_client.get_langfuse_prompt("title-en", chat=messages_for_prompt)
        session_id = request.find_store(
            "unique_id", request.find_store("chat_id", None)
        )

        title_response = (
            await PassthroughChain()
            .create_chain(
                llm_client.llm(max_tokens=200, chat_id=session_id),
                prompt,
                session_id=session_id,
                tags=["title"],
            )
            .ainvoke({})
        )

        return TitleResponse(title=title_response)


citation_bot = CitationBot()
post = citation_bot.post


def load_module_db(module: str, locale: LocaleType) -> VectorStore:
    """Load the module database."""
    logger.info("CitationBot: Loading vector storage (all)")
    print("Loading all scientific work data")
    logger.info("CitationBot: Loading vector storage (all)")
    print("Loading all scientific work data")
    return FAISSVectorDB().load_local(
        str(Path(STRUCTURE_ID).parent / "all"),
        str(Path(STRUCTURE_ID).parent / "all"),
        embeddings,
    )


async def update_chain(
    response_preferences: ResponsePreferences,
    locale: LocaleType,
    messages: list[Message] = None,
    chat_id: str = None,
    requested_purpose: LLMPurpose = None,
    storage: dict | None = None,
) -> RunnableSerializable:
    """Update the chain with the new information."""
    if messages is None:
        messages = []
    logger.info("CitationBot: Updating chain")

    # Log citation bot context variables if available
    if storage:
        citation_context = {}
        if "thesis_title" in storage:
            citation_context["thesis_title"] = storage["thesis_title"]
        if "thesis_task" in storage:
            citation_context["thesis_task"] = storage["thesis_task"]
        if "thesis_deadlines" in storage:
            citation_context["thesis_deadlines"] = storage["thesis_deadlines"]
        if "thesis_information" in storage:
            citation_context["thesis_information"] = storage["thesis_information"]

    lite_llm = await get_llm(locale, requested_purpose)

    prompt = lite_llm.get_langfuse_prompt(
        "citation-chat-en",
        chat=messages,
        prompt_type="chat",
        label="latest",
    )
    metadata = prompt.metadata

    if "citation_role" in prompt.input_variables:
        citation_role = lite_llm.get_langfuse_prompt(
            "citation-description-en",
            prompt_type="text",
        ).format()
        prompt = prompt.partial(citation_role=citation_role)

    prompt = fill_response_preferences(prompt, response_preferences, locale)

    prompt.metadata = metadata
    return chain.create_chain(
        lite_llm.llm_chatopenai(chat_id=chat_id),
        prompt,
    )


@post("/select_topic")
async def select_topic(request: RequestModel) -> Response:
    """Select the topic - now automatically redirects to new guideline."""
    logger.info("CitationBot: Topic selection - redirecting to new guideline")

    # Redirect to the new guideline instead of manual topic selection
    return Response(
        messages=[
            MessageResponse(
                content=(
                    "I'll help you with scientific writing! Let's"
                    " start with a quick check-in.\n\n"
                    "First, where are you today with your writing?"
                ),
                buttons=[
                    Button(
                        chat_message="I'm just getting started",
                        label="I'm just getting started",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "getting_started"},
                        ),
                    ),
                    Button(
                        chat_message="I'm stuck somewhere",
                        label="I'm stuck somewhere",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "stuck"}
                        ),
                    ),
                    Button(
                        chat_message="I have something written, but need feedback",
                        label="I have something written, but need feedback",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "need_feedback"}
                        ),
                    ),
                    Button(
                        chat_message="I just need motivation",
                        label="I just need motivation",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "need_motivation"},
                        ),
                    ),
                ],
            )
        ]
    )


@post("/start_new_session")
async def start_new_session(request: RequestModel) -> Response:
    """Start a new session with the structured guideline."""
    logger.info("CitationBot: Starting new session")
    """Select the topic - now automatically redirects to new guideline."""
    logger.info("CitationBot: Topic selection - redirecting to new guideline")

    # Redirect to the new guideline instead of manual topic selection
    return Response(
        messages=[
            MessageResponse(
                content=(
                    "I'll help you with scientific writing! Let's"
                    " start with a quick check-in.\n\n"
                    "First, where are you today with your writing?"
                ),
                buttons=[
                    Button(
                        chat_message="I'm just getting started",
                        label="I'm just getting started",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "getting_started"},
                        ),
                    ),
                    Button(
                        chat_message="I'm stuck somewhere",
                        label="I'm stuck somewhere",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "stuck"}
                        ),
                    ),
                    Button(
                        chat_message="I have something written, but need feedback",
                        label="I have something written, but need feedback",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "need_feedback"}
                        ),
                    ),
                    Button(
                        chat_message="I just need motivation",
                        label="I just need motivation",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "need_motivation"},
                        ),
                    ),
                ],
            )
        ]
    )


@post("/writing_status")
async def writing_status(request: RequestModel) -> Response:
    """Handle the user's writing status and move to goal orientation."""
    status = request.find_store("status")
    logger.info(f"CitationBot: Writing status - {status}")

    # Automatically select "Scientific work" topic
    return Response(
        messages=[
            MessageResponse(
                content=(
                    "Thanks! To make this session useful: What would you"
                    " like to focus on right now?"
                    "Hi! I'm your writing coach –"
                    " here to support you, not to judge. "
                    "Writing can be messy and hard, and that's totally okay."
                    " Let's take the next step together.\n\n"
                    "First, where are you today with your writing?"
                ),
                buttons=[
                    Button(
                        chat_message="I'm just getting started",
                        label="I'm just getting started",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "getting_started"},
                        ),
                    ),
                    Button(
                        chat_message="I'm stuck somewhere",
                        label="I'm stuck somewhere",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "stuck"}
                        ),
                    ),
                    Button(
                        chat_message="I have something written, but need feedback",
                        label="I have something written, but need feedback",
                        callback=ButtonCallback(
                            endpoint="writing_status", data={"status": "need_feedback"}
                        ),
                    ),
                    Button(
                        chat_message="I just need motivation",
                        label="I just need motivation",
                        callback=ButtonCallback(
                            endpoint="writing_status",
                            data={"status": "need_motivation"},
                        ),
                    ),
                ],
            )
        ]
    )


@post("/goal_orientation")
async def goal_orientation(request: RequestModel) -> Response:
    """Handle goal orientation and move to motivation check."""
    goal = request.find_store("goal")
    logger.info(f"CitationBot: Goal orientation - {goal}")

    return Response(
        messages=[
            MessageResponse(
                content=(
                    "On a scale from 1 to 10 – how motivated do"
                    " you feel to write right now?"
                ),
                buttons=[
                    Button(
                        chat_message="1",
                        label="1️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "1"}
                        ),
                    ),
                    Button(
                        chat_message="2",
                        label="2️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "2"}
                        ),
                    ),
                    Button(
                        chat_message="3",
                        label="3️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "3"}
                        ),
                    ),
                    Button(
                        chat_message="4",
                        label="4️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "4"}
                        ),
                    ),
                    Button(
                        chat_message="5",
                        label="5️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "5"}
                        ),
                    ),
                    Button(
                        chat_message="6",
                        label="6️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "6"}
                        ),
                    ),
                    Button(
                        chat_message="7",
                        label="7️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "7"}
                        ),
                    ),
                    Button(
                        chat_message="8",
                        label="8️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "8"}
                        ),
                    ),
                    Button(
                        chat_message="9",
                        label="9️⃣",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "9"}
                        ),
                    ),
                    Button(
                        chat_message="10",
                        label="🔟",
                        callback=ButtonCallback(
                            endpoint="motivation_check", data={"motivation": "10"}
                        ),
                    ),
                ],
            )
        ]
    )


@post("/motivation_check")
async def motivation_check(request: RequestModel) -> Response:
    """Handle motivation check and provide support if needed."""
    motivation_str = request.find_store("motivation")
    if motivation_str is None:
        motivation = 5  # Default to middle value if not found
    else:
        motivation = int(motivation_str)
    logger.info(f"CitationBot: Motivation check - {motivation}")

    if motivation < 5:
        return Response(
            messages=[
                MessageResponse(
                    content=(
                        "Thanks for being honest. What would help you move"
                        " one point higher?"
                    ),
                    buttons=[
                        Button(
                            chat_message="Less pressure",
                            label="Less pressure",
                            callback=ButtonCallback(
                                endpoint="resource_activation",
                                data={"motivation_help": "less_pressure"},
                            ),
                        ),
                        Button(
                            chat_message="A tiny next step",
                            label="A tiny next step",
                            callback=ButtonCallback(
                                endpoint="resource_activation",
                                data={"motivation_help": "tiny_step"},
                            ),
                        ),
                        Button(
                            chat_message="Some encouragement",
                            label="Some encouragement",
                            callback=ButtonCallback(
                                endpoint="resource_activation",
                                data={"motivation_help": "encouragement"},
                            ),
                        ),
                        Button(
                            chat_message="I don't know",
                            label="I don't know",
                            callback=ButtonCallback(
                                endpoint="resource_activation",
                                data={"motivation_help": "unknown"},
                            ),
                        ),
                    ],
                )
            ]
        )
    else:
        # If motivation is 5 or higher, skip to resource activation
        return Response(
            messages=[
                MessageResponse(
                    content=(
                        "Great! Can you think of a time where writing"
                        " went well for you?"
                        "Even a small moment.\n\n"
                        "What helped you back then?"
                    ),
                    buttons=[
                        Button(
                            chat_message="I had a clear goal",
                            label="I had a clear goal",
                            callback=ButtonCallback(
                                endpoint="micro_goal_setting",
                                data={"resource": "clear_goal"},
                            ),
                        ),
                        Button(
                            chat_message="I had a quiet space",
                            label="I had a quiet space",
                            callback=ButtonCallback(
                                endpoint="micro_goal_setting",
                                data={"resource": "quiet_space"},
                            ),
                        ),
                        Button(
                            chat_message="I wasn't overthinking",
                            label="I wasn't overthinking",
                            callback=ButtonCallback(
                                endpoint="micro_goal_setting",
                                data={"resource": "not_overthinking"},
                            ),
                        ),
                        Button(
                            chat_message="I felt supported",
                            label="I felt supported",
                            callback=ButtonCallback(
                                endpoint="micro_goal_setting",
                                data={"resource": "felt_supported"},
                            ),
                        ),
                        Button(
                            chat_message="Not sure",
                            label="Not sure",
                            callback=ButtonCallback(
                                endpoint="micro_goal_setting",
                                data={"resource": "not_sure"},
                            ),
                        ),
                    ],
                )
            ]
        )


@post("/resource_activation")
async def resource_activation(request: RequestModel) -> Response:
    """Handle resource activation and move to micro goal setting."""
    motivation_help = request.find_store("motivation_help")
    logger.info(f"CitationBot: Resource activation - {motivation_help}")

    return Response(
        messages=[
            MessageResponse(
                content=(
                    "Can you think of a time where writing went well for you?"
                    " Even a small moment.\n\n"
                    "What helped you back then?"
                ),
                buttons=[
                    Button(
                        chat_message="I had a clear goal",
                        label="I had a clear goal",
                        callback=ButtonCallback(
                            endpoint="micro_goal_setting",
                            data={"resource": "clear_goal"},
                        ),
                    ),
                    Button(
                        chat_message="I had a quiet space",
                        label="I had a quiet space",
                        callback=ButtonCallback(
                            endpoint="micro_goal_setting",
                            data={"resource": "quiet_space"},
                        ),
                    ),
                    Button(
                        chat_message="I wasn't overthinking",
                        label="I wasn't overthinking",
                        callback=ButtonCallback(
                            endpoint="micro_goal_setting",
                            data={"resource": "not_overthinking"},
                        ),
                    ),
                    Button(
                        chat_message="I felt supported",
                        label="I felt supported",
                        callback=ButtonCallback(
                            endpoint="micro_goal_setting",
                            data={"resource": "felt_supported"},
                        ),
                    ),
                    Button(
                        chat_message="Not sure",
                        label="Not sure",
                        callback=ButtonCallback(
                            endpoint="micro_goal_setting", data={"resource": "not_sure"}
                        ),
                    ),
                ],
            )
        ]
    )


@post("/micro_goal_setting")
async def micro_goal_setting(request: RequestModel) -> Response:
    """Handle micro goal setting and start the session."""
    resource = request.find_store("resource")
    goal = request.find_store("goal", "explore")  # Default to explore if not set
    logger.info(f"CitationBot: Micro goal setting - resource: {resource}, goal: {goal}")

    # Determine appropriate micro goals based on the user's goal
    if goal == "find_topic":
        micro_goals = [
            "Draft a working title",
            "Sketch a section outline",
            "Talk through my idea with you",
            "Just think aloud for a while",
        ]
    elif goal == "outline_structure":
        micro_goals = [
            "Write 100 words",
            "Sketch a section outline",
            "Talk through my idea with you",
            "Just think aloud for a while",
        ]
    elif goal == "work_section":
        micro_goals = [
            "Write 100 words",
            "Sketch a section outline",
            "Talk through my idea with you",
            "Just think aloud for a while",
        ]
    elif goal == "fix_motivation":
        micro_goals = [
            "Talk through my idea with you",
            "Just think aloud for a while",
            "Write 100 words",
            "Draft a working title",
        ]
    else:  # explore or default
        micro_goals = [
            "Write 100 words",
            "Draft a working title",
            "Sketch a section outline",
            "Talk through my idea with you",
            "Just think aloud for a while",
        ]

    return Response(
        messages=[
            MessageResponse(
                content=(
                    "Great – let's set a tiny goal for today. What would"
                    " feel doable and helpful?"
                ),
                buttons=[
                    Button(
                        chat_message=micro_goal,
                        label=micro_goal,
                        callback=ButtonCallback(
                            endpoint="start_session", data={"micro_goal": micro_goal}
                        ),
                    )
                    for micro_goal in micro_goals
                ],
            )
        ]
    )


@post("/start_session")
async def start_session(request: RequestModel) -> Response:
    """Start the actual session with contextual support."""
    micro_goal = request.find_store("micro_goal")
    logger.info(f"CitationBot: Starting session with micro goal - {micro_goal}")

    return Response(
        messages=[
            MessageResponse(
                content=(
                    "Perfect. Let's dive in. I'll guide you step by step."
                    " Remember: we'll figure this out together.\n\n"
                    f"Your micro goal: **{micro_goal}**\n\n"
                    "I'm ready to help you with any aspect of scientific writing! "
                    "You can ask me questions about citations,"
                    " research methods, paper structure, academic language,"
                    " presentations, or any other scientific writing topic. "
                    "What would you like to start with? Use a suggested option or"
                    " just tell me your own request."
                ),
                buttons=[
                    Button(
                        chat_message="What is a citation?",
                        label="What is a citation?",
                        callback=ButtonCallback(
                            endpoint="open_conversation",
                            data={},
                        ),
                    ),
                    Button(
                        chat_message="How do I structure a scientific paper?",
                        label="How do I structure a scientific paper?",
                        callback=ButtonCallback(
                            endpoint="open_conversation",
                            data={},
                        ),
                    ),
                    Button(
                        chat_message="Tell me about research methods",
                        label="Tell me about research methods",
                        callback=ButtonCallback(
                            endpoint="open_conversation",
                            data={},
                        ),
                    ),
                    Button(
                        chat_message="I have a specific question",
                        label="I have a specific question",
                        callback=ButtonCallback(
                            endpoint="open_conversation",
                            data={},
                        ),
                    ),
                ],
            )
        ]
    )


@post("/open_conversation")
async def open_conversation(request: RequestModel) -> Response:
    """Open conversation endpoint that calls the chat_invoke method."""
    logger.info("CitationBot: Opening conversation")
    return await citation_bot.chat_invoke(request)
