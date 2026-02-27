from enum import Enum
from typing import Union

from pydantic import BaseModel

from bots.base_bot import Features
from framework.api_types.locale_type import LocaleType
from framework.api_types.module import Module, Skill


class TopicType(Enum):
    """Enumeration of topic types."""

    SKILLS = "skills"
    BASIC = "basic"


class Topic(Enum):
    """Enum of all available topics."""

    study_competence_bot = "study_competence"
    citation_bot = "citation"
    passthrough_bot = "passthrough"
    st_buddy = "st"


class TopicModel(BaseModel):
    """Model representing a topic in the application."""

    endpoint: Topic
    title: dict[LocaleType, str]
    short_description: dict[LocaleType, str]
    long_description: dict[LocaleType, str]
    modules: list[Union[Module, Skill]]
    type: TopicType
    features: list[Features] = []
    color: str = "#000000"
    priority: int = 0
    enabled: bool = True


class TopicListModel(BaseModel):
    """Model representing a collection of topics."""

    topics: list[TopicModel]
