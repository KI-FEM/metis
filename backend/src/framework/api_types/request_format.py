import datetime
import logging
import random
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field, ValidationError

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.ai_models import LLMPurpose
from framework.api_types.locale_type import LocaleType
from framework.api_types.response_preferences import ResponsePreferences

logger = logging.getLogger()


class MessageType(Enum):
    """The sender of a message."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class Message(BaseModel):
    """Represents a single chat message.

    This model is used to encapsulate a message exchanged in the chat, including
    the sender, content, and optional metadata.

    Args:
        content (str): The content of the message.
        type (str): The sender of the message (e.g., 'user', 'assistant').
        summary (Optional[str]): Optional summary of the message.

    Returns:
        None

    """

    content: str
    type: MessageType
    timestamp: str


class Summary(Message):
    """The format of a summary message."""

    summary: str


class LearnerModelLearningUnit(BaseModel):
    """A learning unit in the learner model."""

    id: int
    code: str
    name: dict[LocaleType, str] = {"en": "Unit", "de": "Einheit"}
    times_seen: int = 0
    last_seen: Optional[str] = None  # date string
    times_quizzed: int = 0
    times_correct: int = 0
    last_quizzed: Optional[str] = None  # date string
    completed: bool = False


class LearnerModelLearningUnitInternal(BaseModel):
    """Internal representation of a learning unit in the learner model."""

    id: int
    code: str
    name: dict[LocaleType, str] = {"en": "Unit", "de": "Einheit"}
    times_seen: int = 0
    last_seen: Optional[str] = None  # date string
    times_quizzed: int = 0
    times_correct: int = 0
    last_quizzed: Optional[str] = None  # date string
    completed: bool = False
    competence_code: str
    concept_code: str


class LearnerModelConcept(BaseModel):
    """A competence in the learner model."""

    concept_id: int
    concept_code: str
    name: dict[LocaleType, str] = {"en": "Concept", "de": "Konzept"}
    custom_learning_goals: str = ""
    learning_units: dict[str, LearnerModelLearningUnit] = {}
    completed: bool = False


class LearnerModelCompetence(BaseModel):
    """The learner model."""

    competence_id: int
    competence_code: str
    competence_level: int
    concepts: dict[str, LearnerModelConcept] = {}
    name: dict[LocaleType, str] = {"en": "Competence", "de": "Kompetenz"}
    completed: bool = False


class LearnerModel(BaseModel):
    """The learner model."""

    competences: dict[str, LearnerModelCompetence] = {}
    learning_units: dict[str, LearnerModelLearningUnitInternal] = {}

    @staticmethod
    async def init_learner_model(
        db, topic_code: str = "study_competence"
    ) -> "LearnerModel":
        """Initialize an empty learner model.

        This method creates and returns an empty LearnerModel object, which can be
        populated with competences and learning units as the user progresses in their
        learning journey.

        Args:
            db (Database): The database instance for getting competences and LUs.
            topic_code (str): The topic code to initialize the learner model for.

        Returns:
            LearnerModel: An initialized LearnerModel object.

        """
        topic = await db.get_topic_by_code(topic_code)
        competences = await db.get_competence_translations_all_languages(topic.idtopic)
        learner_model = LearnerModel(competences={})
        for competence in competences:
            concepts = await db.get_concepts_for_competence_code_all_languages(
                competence.idcompetence
            )
            concepts_dict = {}
            for concept in concepts:
                # we get all lus
                lus = await db.get_learning_units_by_level_for_learner_model(
                    concept.idconcept, competence_level_id=None
                )

                concepts_dict[concept.code] = LearnerModelConcept(
                    concept_id=concept.idconcept,
                    concept_code=concept.code,
                    name=concept.name,
                    learning_units={
                        lu.code: LearnerModelLearningUnit(
                            id=lu.idlearningunit,
                            code=lu.code,
                            name=lu.name,
                        )
                        for lu in lus
                    },
                )

            learner_model.competences[competence.code] = LearnerModelCompetence(
                competence_id=competence.idcompetence,
                competence_code=competence.code,
                competence_level=1,
                concepts=concepts_dict,
                name=competence.name,
            )

        return learner_model

    @staticmethod
    async def init_learner_model_test(
        request: "RequestModel", db, topic_code: str = "study_competence"
    ) -> "LearnerModel":
        """Initialize an empty learner model for testing.

        This method creates and returns an empty LearnerModel object, which can be
        populated with competences and learning units as the user progresses in their
        learning journey.

        Args:
            request (RequestModel): The request model containing user and session data.
            db (Database): The database instance for getting competences and LUs.
            topic_code (str): The topic code to initialize the learner model for.

        Returns:
            LearnerModel: An initialized LearnerModel object.

        """
        locale = request.locale()
        # TODO update to new learner model format

        concepts = await db.get_concepts(topic_code)
        learner_model = LearnerModelCompetence(concepts={})
        for concept in concepts:
            # initialize with level 1, later we upgrade user with quiz
            competence_level = random.randint(1, 3)  # random level for testing
            learning_units = await db.get_learning_units_for_level(
                concept.idconcept,
                competence_level,
                locale,
            )

            learner_model.concepts[concept.code] = LearnerModelConcept(
                concept_id=concept.idconcept,
                concept_code=concept.code,
                competence_level=competence_level,
                learning_units=[
                    LearnerModelLearningUnit(
                        id=lu.idlearningunit,
                        times_seen=random.randint(0, 5) if competence_level < 2 else 0,
                        last_seen=(
                            datetime.datetime.now()
                            - datetime.timedelta(days=random.randint(1, 30))
                        ).isoformat()
                        if competence_level < 2
                        else None,
                        completed=competence_level == 1,
                    )
                    for lu in learning_units
                ],
            )

        return learner_model

    def save_learner_model(self) -> "LearnerModel":
        """Reformat the internal representation back into the LearnerModel."""
        # Update learner model from the internal representation
        for competence in self.competences.values():
            concepts_completed = True
            for concept in competence.concepts.values():
                lus_completed = True
                for lu in concept.learning_units.values():
                    # update the LU of the learner model from the internal LU
                    internal_lu = self.learning_units[lu.code]
                    lu.times_seen = internal_lu.times_seen
                    lu.last_seen = internal_lu.last_seen
                    lu.times_quizzed = internal_lu.times_quizzed
                    lu.last_quizzed = internal_lu.last_quizzed
                    lu.completed = internal_lu.completed

                    # calculate if all LUs are completed
                    lus_completed = lus_completed and lu.completed

                concept.completed = lus_completed
                # calculate if all concepts are completed
                concepts_completed = concepts_completed and concept.completed

            competence.completed = concepts_completed

        self.learning_units = {}
        return self

    def get_completed_luids(self) -> list[int]:
        """Get a list of all completed learning unit IDs."""
        return [lu.id for lu in self.learning_units.values() if lu.completed]


class RequestModel(BaseModel):
    """Request model for chat and bot endpoints.

    This model contains all information sent from the frontend to the backend,
    including chat history, user data, and session state.

    Args:
        id (str): The unique identifier for the request, typically msg timestamp.
        chat_history (list[Message]): The list of previous messages in the conversation.
        language (str): The language code for localization.
        storage (dict): Key-value store for session-specific data.
        streaming (bool): Whether the response should be streamed.
        response_preferences (ResponsePreferences):
            How the user wants the response to be tailored.
        llm_purpose (Optional[str]): Purpose for which the LLM should be auto-selected.

    Returns:
        None

    """

    id: str
    language: str
    chat_history: list[Union[Message, Summary]]
    storage: dict[str, Union[str, int, float, list, dict, LearnerModel]] = {}
    llm_purpose: Optional[LLMPurpose] = Field(
        None,
        description="The purpose of the LLM to use (e.g., 'optimal' or 'reasoning')",
    )
    response_preferences: ResponsePreferences
    streaming: bool = False

    def locale(self) -> LocaleType:
        """Get the locale for the request.

        Returns the locale type based on the language code provided in the request.

        Args:
            None

        Returns:
            LocaleType: The locale type for the request.

        """
        return LocaleType[self.language.upper()]

    def find_store(self, key: str, default=None) -> Union[str, None]:
        """Find the value of a store by key."""
        if key in self.storage:
            return self.storage[key]
        return default

    async def learner_model(self, db=None) -> LearnerModel:
        """Get the learner model from storage."""
        lm_data = self.storage.get("learner_model", None)
        if lm_data is None:
            if db is None:
                return LearnerModel()
            init_model = await LearnerModel.init_learner_model(db)
            lm_data = init_model.model_dump()
            self.storage["learner_model"] = lm_data

        try:
            learner_model = LearnerModel.model_validate(lm_data)
        except ValidationError as e:
            logger.info(f"Could not validate learner model: {e}")
            # maybe it is an old version, try to convert
            if "concepts" in lm_data and db is not None:
                try:
                    # old version with concepts only
                    new_lm = await LearnerModel.init_learner_model(db)
                    competences = {}
                    for concept_code, concept_data in lm_data["concepts"].items():
                        if "competence_code" in concept_data:
                            new_competence = new_lm.competences[
                                concept_data["competence_code"]
                            ]
                            concept_name = new_competence.concepts[concept_code].name
                            concept = LearnerModelConcept(
                                concept_id=concept_data.get("concept_id", 0),
                                concept_code=concept_code,
                                learning_units={
                                    lu_data["code"]: LearnerModelLearningUnit(**lu_data)
                                    for lu_data in concept_data.get(
                                        "learning_units", []
                                    )
                                },
                                name=concept_name,
                            )
                            if concept_data["competence_code"] not in competences:
                                competences[concept_data["competence_code"]] = (
                                    LearnerModelCompetence(
                                        competence_id=new_competence.competence_id,
                                        name=new_competence.name,
                                        competence_code=new_competence.competence_code,
                                        competence_level=concept_data[
                                            "competence_level"
                                        ],
                                        concepts={concept_code: concept},
                                    )
                                )
                            else:
                                competences[concept_data["competence_code"]].concepts[
                                    concept_code
                                ] = concept

                    learner_model = LearnerModel(competences=competences)
                    self.storage["learner_model"] = learner_model.model_dump()
                except Exception as e:
                    logger.info(
                        "Could not convert old learner model format, returning empty "
                        f"model. Error: {e}"
                    )
                    learner_model = LearnerModel()
            else:
                logger.info("Could not validate learner model, returning empty model.")
                learner_model = LearnerModel()

        # also save internal representation
        internal_lus = {}
        for competence in learner_model.competences.values():
            for concept in competence.concepts.values():
                for lu in concept.learning_units.values():
                    internal_lu = LearnerModelLearningUnitInternal(
                        id=lu.id,
                        code=lu.code,
                        name=lu.name,
                        times_seen=lu.times_seen,
                        last_seen=lu.last_seen,
                        times_quizzed=lu.times_quizzed,
                        times_correct=lu.times_correct,
                        last_quizzed=lu.last_quizzed,
                        completed=lu.completed,
                        competence_code=competence.competence_code,
                        concept_code=concept.concept_code,
                    )
                    internal_lus[lu.code] = internal_lu

        learner_model.learning_units = internal_lus
        return learner_model

class CommentRequestModel(BaseModel):
    """Request model for adding comments to messages.

    Args:
        comment (str): The comment to be added to the message.
        trace_id (str): The trace ID associated with the message.

    Returns:
        None

    """

    vote: Optional[int]
    comment: str
    trace_id: str

class MessageVoteRequest(BaseModel):
    """Request model for voting on messages.

    Args:
        vote (int): The vote value, typically 1 for upvote and -1 for downvote.
        trace_id (str): The trace ID associated with the message.
        
    Returns:
        None
    
    """

    vote: int
    trace_id: str
    