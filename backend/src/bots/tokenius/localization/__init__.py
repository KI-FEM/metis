"""Module for localization of Tokenius messages."""

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
