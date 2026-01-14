"""Response preferences module for localized preference scales."""

import sys
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString


class ResponsePreferences(BaseModel):
    """The desired preferences for the response message.

    Each value must be an integer from 0 to 4, where 2 is the neutral default.
    """

    detail: int
    illustration: int
    language_style: int
    humour: int
    creativity: int
    emojis: int


PREFERENCE_SCALE_KEYS = {
    "preferences_lod": "detail",
    "preferences_ill": "illustration",
    "preferences_las": "language_style",
    "preferences_hum": "humour",
    "preferences_cre": "creativity",
    "preferences_emo": "emojis",
}

# Mapping of preference scales to localized adjectives
# Each scale maps integer values (0-4) to LocalizedString objects
PREFERENCE_SCALE_LABELS = {
    "detail": {
        0: LocalizedString("brief", "knapp"),
        1: LocalizedString("general", "allgemein"),
        2: LocalizedString("thorough", "ausführlich"),
        3: LocalizedString("nuanced", "nuanciert"),
        4: LocalizedString("in-depth", "tiefgründig"),
    },
    "illustration": {
        0: LocalizedString("abstract", "abstrakt"),
        1: LocalizedString("implied", "theoretisch"),
        2: LocalizedString("illustrative", "beispielhaft"),
        3: LocalizedString("concrete", "konkret"),
        4: LocalizedString("narrative", "narrativ"),
    },
    "language_style": {
        0: LocalizedString("colloquial", "umgangssprachlich"),
        1: LocalizedString("casual", "locker"),
        2: LocalizedString("neutral", "neutral"),
        3: LocalizedString("refined", "gewählt, präzise"),
        4: LocalizedString("eloquent", "eloquent"),
    },
    "humour": {
        0: LocalizedString("serious", "ernst"),
        1: LocalizedString("factual", "sachlich"),
        2: LocalizedString("light-hearted", "heiter"),
        3: LocalizedString("amusing", "unterhaltsam"),
        4: LocalizedString("witty", "witzig"),
    },
    "creativity": {
        0: LocalizedString("conventional", "konventionell"),
        1: LocalizedString("conforming", "funktional"),
        2: LocalizedString("original", "originell"),
        3: LocalizedString("inventive", "ideenreich"),
        4: LocalizedString("imaginative", "phantasievoll"),
    },
    "emojis": {
        0: LocalizedString("sparse", "sparsam"),
        1: LocalizedString("occasional", "gelegentlich"),
        2: LocalizedString("moderate", "moderat"),
        3: LocalizedString("expressive", "ausgeprägt"),
        4: LocalizedString("abundant", "reichlich"),
    },
}


def fill_response_preferences(
    prompt: PromptTemplate,
    response_preferences: ResponsePreferences,
    locale: LocaleType,
) -> PromptTemplate:
    """Fill the prompt with response preferences, if required."""
    prompt_response_preferences = {}
    if set(PREFERENCE_SCALE_KEYS.keys()) & set(prompt.input_variables):
        for prompt_var, scale_label in PREFERENCE_SCALE_KEYS.items():
            preference_number = response_preferences.model_dump()[scale_label]
            preference_label = PREFERENCE_SCALE_LABELS[scale_label][
                preference_number
            ].get(locale)
            prompt_response_preferences[prompt_var] = (
                f"{preference_label} ({preference_number + 1})"
            )
        return prompt.partial(**prompt_response_preferences)

    return prompt
