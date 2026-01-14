import json
import logging
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
from framework.api_types.locale_type import LocaleType
from framework.api_types.module import Module, Skill, SkillLevel
from framework.api_types.request_format import LearnerModel
from framework.api_types.response_format import Source
from framework.db.db_types import (
    ChunkDB,
    CompetenceDB,
    CompetenceLevelTranslationDB,
    CompetenceTranslationAllLanguagesDB,
    CompetenceTranslationDB,
    ConceptDB,
    ConceptTranslationDB,
    ConceptTranslationJoinedDB,
    ConceptTranslationMultiLanguage,
    JoinedChunk,
    LanguageDB,
    LearningUnitCombined,
    LearningUnitForLearnerModel,
    LightCompetenceTranslation,
    PurposeCompleteDB,
    PurposeDB,
    TopicDB,
)

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseMock:
    """A class to handle database operations using asyncpg."""

    def __init__(self):
        """Initialize the database connection."""
        self.connection = None
        self.book_lang_comp_chunks = set()
        self.book_lang_comp_subdocs = set()

    async def get_competence_translated_by_code(
        self, competence_code: str, locale: LocaleType
    ) -> CompetenceTranslationDB:
        """Get a competence by its code and its associated translation for a locale."""
        return CompetenceTranslationDB(
            idcompetence=1,
            idlanguage=1,
            name="Resilienz",
            description="Beschreibung Resilienz",
        )

    async def get_competence_translated_light(
        self, competence_code: str, locale: LocaleType
    ) -> LightCompetenceTranslation:
        """Get a light competence translation by its ID and locale."""
        return LightCompetenceTranslation(
            idcompetence=1,
            code="resilience",
            name="Resilienz",
            description="Beschreibung Resilienz",
            language_code="de",
        )

    async def get_competences_translated_light(
        self, locale: LocaleType
    ) -> list[LightCompetenceTranslation]:
        """Get all competences with their translations for a specific locale in a light format."""
        return [
            LightCompetenceTranslation(
                idcompetence=1,
                code="resilience",
                name="Resilienz",
                description="Beschreibung Resilienz",
                language_code="de",
            )
        ]

    async def get_skill_by_code(self, skill_code: str) -> Skill:
        """Get a skill by its code."""
        return Skill(
            id=1,
            code=skill_code,
            title={"de": "Resilienz", "en": "Resilience"},
            description={
                "de": "Beschreibung Resilienz",
                "en": "Description Resilience",
            },
            levels=[],  # TODO
        )

    async def get_skills(self, topic_id: int) -> list[Skill]:
        """Get all skills from the database."""
        # Fetch all competence levels
        return [
            Skill(
                id=1,
                code="resilience",
                title={"de": "Resilienz", "en": "Resilience"},
                description={
                    "de": "Beschreibung Resilienz",
                    "en": "Description Resilience",
                },
                levels=[
                    SkillLevel(
                        id=1,
                        code="resilience_level_1",
                        title={
                            "de": "Resilienz Stufe 1",
                            "en": "Resilience Level 1",
                        },
                        description={
                            "de": "Beschreibung Resilienz Stufe 1",
                            "en": "Description Resilience Level 1",
                        },
                        learning_goals={
                            "de": "Lernziele Resilienz Stufe 1",
                            "en": "Learning Goals Resilience Level 1",
                        },
                    )
                ],
            ),
            Skill(
                id=2,
                code="self_efficacy",
                title={"de": "Selbstwirksamkeit", "en": "Self-Efficacy"},
                description={
                    "de": "Beschreibung Selbstwirksamkeit",
                    "en": "Description Self-Efficacy",
                },
                levels=[
                    SkillLevel(
                        id=2,
                        code="self_efficacy_level_1",
                        title={
                            "de": "Selbstwirksamkeit Stufe 1",
                            "en": "Self-Efficacy Level 1",
                        },
                        description={
                            "de": "Beschreibung Selbstwirksamkeit Stufe 1",
                            "en": "Description Self-Efficacy Level 1",
                        },
                        learning_goals={
                            "de": "Lernziele Selbstwirksamkeit Stufe 1",
                            "en": "Learning Goals Self-Efficacy Level 1",
                        },
                    )
                ],
            ),
        ]

    async def get_topic_by_code(self, topic_code: str) -> TopicDB:
        """Get a topic by its code."""
        return TopicDB(
            idtopic=1,
            code=topic_code,
            createdat="2023-01-01 00:00:00",
            updatedat="2023-01-01 00:00:00",
            enabled=True,
        )

    async def get_modules(self, topic_id: int) -> list[Module]:
        """Get all modules (competences) for a specific topic."""
        return [
            Module(
                id=1,
                code="module_1",
                title={LocaleType.EN: "Module 1", LocaleType.DE: "Modul 1"},
            )
        ]

    async def get_competence_level_translated(
        self, competence_level_id: int, locale: LocaleType
    ) -> CompetenceLevelTranslationDB:
        """Get a competence level by its ID and its associated translation."""
        return CompetenceLevelTranslationDB(
            idcompetencelevel=1,
            idlanguage=1,
            name="Novize",
            description="Beschreibung Novize",
        )

    async def get_chunks_joined(self, chunkids: list[int]) -> list[JoinedChunk]:
        """Get multiple chunks and their related entities by chunk IDs."""
        return [
            JoinedChunk(
                chunk=ChunkDB(
                    idchunk=1,
                    content="Sample content",
                    embedding=[],  # Assuming embedding is stored as a list or array
                    idbook=1,
                    idlanguage=1,
                    idtopic=1,
                    idcompetence=1,
                    idsubdocument=1,
                    createdat="2023-01-01 00:00:00",
                    updatedat="2023-01-01 00:00:00",
                    enabled=True,
                ),
                chunk_language=LocaleType.EN,
                source=Source(
                    title="Sample Book",
                    chunk="Sample content",
                    thumbnail=None,  # Assuming thumbnail is not available in this query
                    year=2023,
                    authors=["Author One", "Author Two"],
                    original_language=LocaleType.EN,
                ),
                competence_id=1,
                competence_code="COMP1",
            )
        ]

    async def get_language(self, language_code: str) -> LanguageDB:
        """Get a language by its code."""
        return LanguageDB(
            idlanguage=1,
            name="German",
            createdat="2023-01-01 00:00:00",
            updatedat="2023-01-01 00:00:00",
            enabled=True,
            code=language_code,
        )

    async def get_learning_units_joined(
        self, learning_unit_ids: list[int], locale: LocaleType
    ) -> list[LearningUnitCombined]:
        """Get learning units by their IDs and locale."""
        return [
            LearningUnitCombined(
                idlearningunit=1,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel",
                task="Aufgabe",
                solution="Lösung",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            ),
            LearningUnitCombined(
                idlearningunit=2,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel2",
                task="Aufgabe2",
                solution="Lösung2",
                name="Lerneinheit 2",
                code="LU_understand_resilience_concept",
            ),
        ]

    async def get_competence_translations_all_languages(
        self, topic_id: int = 1
    ) -> list[CompetenceTranslationAllLanguagesDB]:
        """Get all competences with their translations for a specific locale."""
        return [
            CompetenceTranslationAllLanguagesDB(
                idcompetence=1,
                code="COMP1",
                name={"de": "Kompetenz 1", "en": "Competence 1"},
                description={"de": "Beschreibung 1", "en": "Description 1"},
            )
        ]

    async def get_concepts_for_competence_code_all_languages(
        self, idcompetence: int
    ) -> list[ConceptTranslationMultiLanguage]:
        """Get concepts for a specific competence in all languages."""
        return [
            ConceptTranslationMultiLanguage(
                idconcept=idcompetence,
                code="Concept_personal_resilience",
                name={"de": "Persönliche Resilienz", "en": "Personal Resilience"},
                description={
                    "de": "Beschreibung der persönlichen Resilienz",
                    "en": "Description of personal resilience",
                },
            )
        ]

    async def get_learning_units_for_competence_and_level(
        self,
        competence_id: int,
        competence_level_id: int,
        locale: LocaleType,
        excluded_luids: list[int] = None,
        only_luids: list[int] = None,
    ) -> list[LearningUnitCombined]:
        """Get learning units for a specific competence and level."""
        return [
            LearningUnitCombined(
                idlearningunit=1,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel",
                task="Aufgabe",
                solution="Lösung",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            ),
            LearningUnitCombined(
                idlearningunit=2,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel2",
                task="Aufgabe2",
                solution="Lösung2",
                name="Lerneinheit 2",
                code="LU_understand_resilience_concept",
            ),
        ]

    async def get_following_learning_units(
        self,
        completed_learning_unit_ids: list[int],
        selected_competence_id: int,
        cur_competence_level_id: int,
        locale: LocaleType,
    ) -> list[LearningUnitCombined]:
        """Get learning units that the user will need to learn next.

        This method retrieves learning units that are not in the completed list
        and are associated with the specified competence and current competence level.
        The DB returns the units that are still missing of the current competence level.
        """
        return [
            LearningUnitCombined(
                idlearningunit=1,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel",
                task="Aufgabe",
                solution="Lösung",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            ),
            LearningUnitCombined(
                idlearningunit=2,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel2",
                task="Aufgabe2",
                solution="Lösung2",
                name="Lerneinheit 2",
                code="LU_understand_resilience_concept",
            ),
        ]

    async def get_competence_by_code(self, competence_code: str) -> CompetenceDB:
        """Get a competence by its code."""
        return CompetenceDB(
            idcompetence=1,
            createdat="2023-01-01 00:00:00",
            updatedat="2023-01-01 00:00:00",
            enabled=True,
            code=competence_code,
            idtopic=1,
        )

    async def get_concepts_not_completed_yet(
        self,
        competence_id: int,
        competence_level_id: int,
        completed_luids: list[int],
        language_code: str,
    ) -> list[ConceptTranslationDB]:
        """Get concepts that have not been completed yet."""
        # This method simulates the retrieval of concepts that are not yet completed
        return [
            ConceptTranslationDB(
                idconcept=1,
                idlanguage=1,
                name="Concept 1",
                description="Description of Concept 1",
            ),
            ConceptTranslationDB(
                idconcept=2,
                idlanguage=1,
                name="Concept 2",
                description="Description of Concept 2",
            ),
        ]

    async def get_learningunits_for_competence(
        self, idcompetence: int, idcompetencelevel: int, completed_luids: list[int]
    ) -> list[LearningUnitCombined]:
        """Get learning units for a specific competence and competence level."""
        ret_learning_units = [
            LearningUnitCombined(
                idlearningunit=69,
                idstep=69,
                idcompetencelevel=69,
                idconcept=69,
                idlanguage=69,
                language_code="en",
                learning_goal="Learning Goal",
                task="Task",
                solution="Solution",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            )
        ]

        return ret_learning_units

    async def get_concepts(self, topic_code: str) -> list[ConceptDB]:
        """Get all concepts from the database."""
        return [
            ConceptDB(
                idconcept=1,
                createdat="2023-01-01 00:00:00",
                updatedat="2023-01-01 00:00:00",
                enabled=True,
                code="concept_1",
            )
        ]

    async def get_learning_units_for_level(
        self,
        concept_id: int,
        competence_level_id: int,
        locale: LocaleType,
        excluded_luids: list[int] = None,
        only_luids: list[int] = None,
    ) -> list[LearningUnitCombined]:
        """Get learning units for a specific concept and competence level."""
        return [
            LearningUnitCombined(
                idlearningunit=69,
                idstep=69,
                idcompetencelevel=69,
                idconcept=69,
                idlanguage=69,
                language_code="en",
                learning_goal="Learning Goal",
                task="Task",
                solution="Solution",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            )
        ]

    async def get_following_learning_units_for_learner_model(
        self,
        learner_model: LearnerModel,
        locale: LocaleType,
    ) -> list[LearningUnitCombined]:
        """Get learning units that the user will need to learn next based on their learner model.

        This method retrieves learning units that are not in the completed list
        and are associated with the selected competence and current competence level.
        The DB returns the units that are still missing of the current competence level.
        """
        return [
            LearningUnitCombined(
                idlearningunit=1,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel",
                task="Aufgabe",
                solution="Lösung",
                name="Lerneinheit 1",
                code="LU_create_resilience_example",
            ),
            LearningUnitCombined(
                idlearningunit=2,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                idlanguage=1,
                language_code="de",
                learning_goal="Lernziel2",
                task="Aufgabe2",
                solution="Lösung2",
                name="Lerneinheit 2",
                code="LU_understand_resilience_concept",
            ),
        ]

    async def get_learning_units_by_level_for_learner_model(
        self, concept_id: int, competence_level_id: int
    ) -> list[LearningUnitForLearnerModel]:
        """Get learning units for a specific concept and competence level."""
        return [
            LearningUnitForLearnerModel(
                idlearningunit=1,
                idstep=1,
                idcompetencelevel=1,
                idconcept=1,
                code="LU_create_resilience_example",
                name={
                    "de": "Erstelle Resilienz Beispiel",
                    "en": "Create Resilience Example",
                },
            )
        ]

    async def get_competence_for_concept(self, concept_id: int) -> CompetenceDB:
        """Get a competence by its ID."""
        return CompetenceDB(
            idcompetence=1,
            createdat="2023-01-01 00:00:00",
            updatedat="2023-01-01 00:00:00",
            enabled=True,
            code="competence_1",
            idtopic=1,
        )

    async def get_concept_by_code(self, concept_code: str) -> ConceptDB:
        """Get a concept by its code."""
        return ConceptDB(
            idconcept=1,
            createdat="2023-01-01 00:00:00",
            updatedat="2023-01-01 00:00:00",
            enabled=True,
            code=concept_code,
        )

    async def execute(self, query: str, params=None):
        """Mock execute method."""
        return "Mocked execute result"

    async def get_concepts_for_competence_code(
        self, idcompetence: int, locale: LocaleType
    ) -> list[ConceptTranslationJoinedDB]:
        """Get concepts for a specific competence."""
        return [
            ConceptTranslationJoinedDB(
                idconcept=1,
                idlanguage=1,
                code="LU_personal_resilience",
                name="Personal Resilience",
                description="Individual resilience factors",
            ),
            ConceptTranslationJoinedDB(
                idconcept=2,
                idlanguage=1,
                code="LU_social_context",
                name="Social Context",
                description="Resilience in social environments",
            ),
        ]

    async def get_config_value(self, key: str, environment: str) -> Optional[str]:
        """Get a configuration value by key."""
        if key == "MODELS_REFRESH_THRESHOLD":
            return 100
        if key == "AI_MODELS":
            return json.dumps(
                {
                    "purposes": [
                        {
                            "id": "optimal",
                            "label": {"en": "Optimal", "de": "Optimal"},
                            "description": {
                                "en": "Optimal model for everyday tasks.",
                                "de": "Optimales Modell für alltägliche Aufgaben.",
                            },
                            "icon": "fas fa-check-circle",
                            "models": [
                                "llama-3.3",
                                "llama-3.1-sauerkrautlm-70b",
                            ],
                        },
                        {
                            "id": "reasoning",
                            "label": {"en": "Analytical", "de": "Analytisch"},
                            "description": {
                                "en": "Model for deep thinking tasks.",
                                "de": "Modell für tiefes Denken.",
                            },
                            "icon": "fas fa-brain",
                            "models": [
                                "llama-3.1-sauerkrautlm-70b",
                            ],
                        },
                    ]
                }
            )
        if key == "KEEP_LAST_MESSAGES_UNTIL":
            return 16
        if key == "MAX_MESSAGES_BEFORE_SUMMARIZATION":
            return 64
        return "some_value"

    async def get_all_config_values(self, environment: str) -> dict[str, str]:
        """Get all configuration values for a specific environment."""
        return {
            "MODELS_REFRESH_THRESHOLD": 100,
        }

    async def set_config_value(self, key: str, value: str, environment: str):
        """Set a configuration value by key."""
        if key is None:
            return  # nothing to do
        # Mock setting the configuration value
        logger.info(f"Set config {key} to {value} for environment {environment}")

    async def get_purpose(self, code: str) -> Optional[PurposeDB]:
        """Get a purpose by its code."""
        if code == "optimal":
            return PurposeDB(
                idpurposes=1,
                code=code,
                icon="fas fa-check-circle",
                models=["llama-3.3", "llama-3.1-sauerkrautlm-70b"],
                enabled=True,
            )
        if code == "reasoning":
            return PurposeDB(
                idpurposes=2,
                code=code,
                icon="fas fa-brain",
                models=["llama-3.1-sauerkrautlm-70b"],
                enabled=True,
            )
        return None

    async def get_all_purposes(self) -> list[PurposeDB]:
        """Get all purposes."""
        return [
            PurposeDB(
                idpurposes=1,
                code="optimal",
                icon="fas fa-check-circle",
                models=["llama-3.3", "llama-3.1-sauerkrautlm-70b"],
                enabled=True,
            ),
            PurposeDB(
                idpurposes=2,
                code="reasoning",
                icon="fas fa-brain",
                models=["llama-3.1-sauerkrautlm-70b"],
                enabled=True,
            ),
        ]

    async def get_all_purposes_complete(self) -> list[PurposeCompleteDB]:
        """Get all purposes with translations for name and description."""
        return [
            PurposeCompleteDB(
                idpurposes=1,
                code="optimal",
                icon="fas fa-check-circle",
                models=["llama-3.3", "llama-3.1-sauerkrautlm-70b"],
                enabled=True,
                name={"en": "Optimal", "de": "Optimal"},
                description={
                    "en": "Optimal model for everyday tasks.",
                    "de": "Optimales Modell für alltägliche Aufgaben.",
                },
            ),
            PurposeCompleteDB(
                idpurposes=2,
                code="reasoning",
                icon="fas fa-brain",
                models=["llama-3.1-sauerkrautlm-70b"],
                enabled=True,
                name={"en": "Analytical", "de": "Analytisch"},
                description={
                    "en": "Model for deep thinking tasks.",
                    "de": "Modell für tiefes Denken.",
                },
            ),
        ]

    async def update_purpose(self, purpose: PurposeDB) -> bool:
        """Update a purpose."""
        return True
