"""Bots for different topics."""

__all__ = [
    "citation_bot",
    "grumci_buddy",
    "passthrough_bot",
    "st_buddy",
    "study_competence_bot",
    "tokenius",
    'dissy',
]

from bots.citation.citation_bot import citation_bot
from bots.dissy.chatbot import dissy
from bots.grumci.grumci_bot import grumci_buddy
from bots.passthrough.passthrough_bot import passthrough_bot
from bots.st.st_buddy import st_buddy
from bots.study.study_competence_bot import study_competence_bot
from bots.tokenius.chatbot import tokenius