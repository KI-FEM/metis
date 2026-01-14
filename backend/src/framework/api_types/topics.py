from enum import Enum
from typing import Union

from pydantic import BaseModel

from bots.base_bot import Features, TopicType
from framework.api_types.locale_type import LocaleType
from framework.api_types.module import Module, Skill


class Topic(Enum):
    """Enum of all available static bot topics."""

    study_competence_bot = "study_competence"
    citation_bot = "citation"
    passthrough_bot = "passthrough"
    st_buddy = "st"
    grumci_buddy = "grumci"
    maschbau = "pa"
    tokenius = "tokenius"
    dissy = "dissy"


class TopicModel(BaseModel):
    """Model representing a topic in the application."""

    endpoint: str
    title: dict[LocaleType, str]
    short_description: dict[LocaleType, str]
    long_description: dict[LocaleType, str]
    modules: list[Module | Skill]
    type: TopicType
    features: list[Features] = []
    color: str = "#000000"
    avatar: Union[str, None] = None
    priority: int = 0
    optional: bool = True
    enabled: bool = True
    tag: Union[str, None] = None


class TopicListModel(BaseModel):
    """Model representing a collection of topics."""

    topics: list[TopicModel]
