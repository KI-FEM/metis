from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from framework.api_types.locale_type import LocaleType
from framework.api_types.response_format import Source


class LanguageDB(BaseModel):
    """DB model for languages."""

    idlanguage: int
    name: str
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool
    code: str


class BookDB(BaseModel):
    """DB model for books."""

    idbook: int
    title: str
    idlanguage: int
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool
    authors: list[str] | None = None
    code: str
    year: int | None = None


class ChunkDB(BaseModel):
    """DB model for chunks of text used for embedding."""

    idchunk: int
    content: str | None = None
    embedding: List[float] | None = None  # vector(1024) as list of floats
    idbook: int
    idlanguage: int
    idcompetence: int
    idtopic: int
    idsubdocument: int | None = None
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class SubDocumentDB(BaseModel):
    """DB model for subdocuments of books, used for embedding/retrieving."""

    idsubdocument: int
    content: str | None = None
    idbook: int
    idlanguage: int
    idcompetence: int
    idtopic: int
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class CompetenceDB(BaseModel):
    """DB model for competences - larger units of knowledge or skills."""

    idcompetence: int
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool
    code: str
    idtopic: int


class JoinedChunk(BaseModel):
    """DB Model for a chunk joined with related entities."""

    chunk: ChunkDB
    chunk_language: LocaleType
    source: Source
    competence_id: int | None = None
    competence_code: str | None = None
    subdocument_content: str | None = None


class CompetenceLevelDB(BaseModel):
    """DB model for competence levels - specific levels within a competence."""

    idcompetencelevel: int
    code: str
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class CompetenceLevelTranslationDB(BaseModel):
    """DB model for translations of competence levels."""

    idcompetencelevel: int
    idlanguage: int
    name: str
    description: str | None = None


class CompetenceTranslationDB(BaseModel):
    """DB model for translations of competences."""

    idcompetence: int
    idlanguage: int
    name: str
    description: str | None = None


class CompetenceTranslationAllLanguagesDB(BaseModel):
    """DB model for translations of competences."""

    idcompetence: int
    code: str
    name: dict[LocaleType, str]
    description: Optional[dict[LocaleType, str]] = None


class LightCompetenceTranslation(BaseModel):
    """A lightweight representation of a competence translation."""

    idcompetence: int
    code: str
    name: str
    description: str
    language_code: str


class ConceptDB(BaseModel):
    """DB model for concepts - fundamental ideas or topics within a competence."""

    idconcept: int
    code: str
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class ConceptTranslationDB(BaseModel):
    """DB model for translations of concepts."""

    idconcept: int
    idlanguage: int
    name: str
    description: str | None = None


class ConceptTranslationJoinedDB(BaseModel):
    """DB model for translations plus code of concepts."""

    idconcept: int
    idlanguage: int
    code: str
    name: str
    description: str | None = None


class ConceptTranslationMultiLanguage(BaseModel):
    """DB model for translations plus code of concepts."""

    idconcept: int
    code: str
    name: dict[LocaleType, str]
    description: Optional[dict[LocaleType, str]] = None


class CompetenceConceptDB(BaseModel):
    """DB model for the relationship between competences and concepts."""

    idcompetence: int
    idconcept: int
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class LearningStepDB(BaseModel):
    """DB model for learning steps - individual steps in a learning process."""

    idstep: int
    code: str
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class LearningStepTranslationDB(BaseModel):
    """DB model for translations of learning steps."""

    idstep: int
    idlanguage: int
    name: str | None = None
    description: str | None = None


class LearningUnitDB(BaseModel):
    """DB model for learning units - smallest entities in the learning hierarchy."""

    idlearningunit: int
    idstep: int
    idconcept: int
    idcompetencelevel: int
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool
    code: str | None = None


class LearningUnitTranslationDB(BaseModel):
    """DB model for translations of learning units."""

    idlearningunit: int
    idlanguage: int
    learninggoal: str | None = None
    task: str | None = None
    solution: str | None = None
    name: str | None = None


class LearningUnitCombined(BaseModel):
    """Combined model for learning unit with its competence and competence level."""

    idlearningunit: int
    idstep: int
    idcompetencelevel: int
    idconcept: int
    idlanguage: int
    language_code: str
    learning_goal: str
    task: str
    solution: str
    name: str
    code: str


class LearningUnitForLearnerModel(BaseModel):
    """Model for learning unit in the learner model context."""

    idlearningunit: int
    idstep: int
    idcompetencelevel: int
    idconcept: int
    code: str
    name: dict[str, str]


class TopicDB(BaseModel):
    """DB model for topics, i.e. the different bots."""

    idtopic: int
    code: str
    createdat: datetime
    updatedat: datetime | None = None
    enabled: bool


class TopicTranslationDB(BaseModel):
    """DB model for translations of topics."""

    idtopic: int
    idlanguage: int
    name: str | None = None
    description: str | None = None

class PurposeDB(BaseModel):
    """DB model for LLM purposes."""

    idpurposes: int
    code: str
    icon: Optional[str] = None
    models: list[str]
    enabled: bool

class PurposeCompleteDB(BaseModel):
    """DB model for LLM purposes with translations."""

    idpurposes: int
    code: str
    icon: Optional[str] = None
    models: list[str]
    enabled: bool
    name: dict[LocaleType, str]
    description: dict[LocaleType, str]