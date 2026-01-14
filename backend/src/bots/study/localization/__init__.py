"""Module for localization of study bot messages."""

from framework.api_types.locale_type import LocaleType

from .base_local import BaseLocalization
from .de import german_localization
from .en import english_localization

localization = {
    LocaleType.EN: english_localization,
    LocaleType.DE: german_localization,
}


def get_localization(locale: LocaleType) -> BaseLocalization:
    """Get the localization for the given locale."""
    if locale not in localization:
        return f"Failed to find localization for locale {locale}."
    return localization[locale]

def get_localization_str(locale_str: str) -> BaseLocalization:
    """Get the localization for the given locale."""
    locale = LocaleType[locale_str.upper()]
    if locale not in localization:
        return f"Failed to find localization for locale {locale}."
    return get_localization(locale)