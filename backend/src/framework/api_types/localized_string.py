from framework.api_types.locale_type import LocaleType


class LocalizedString:
    """Represents a string with multiple localizations.

    This class is used to store and retrieve localized versions of a string for
    different languages.

    Args:
        en (str): The English version of the string.
        de (Optional[str]): The German version of the string.
        ... (other languages as needed)

    Returns:
        None

    """

    def __init__(self, en_string: str, de_string: str = "") -> None:
        """Initialize the localized string."""
        self.strings = {LocaleType.EN: en_string}
        if de_string:
            self.strings[LocaleType.DE] = de_string

    def en(self) -> str:
        """Return the English string."""
        return self.strings.get(LocaleType.EN, "")

    def de(self) -> str:
        """Return the German string."""
        return self.strings.get(LocaleType.DE, "")

    def add_locale(self, locale: LocaleType, string: str) -> None:
        """Add a string for a specific locale."""
        self.strings[locale] = string

    def get(self, locale: LocaleType) -> str:
        """Return the string for a specific locale."""
        return self.strings.get(locale, "")

    def __str__(self) -> str:
        """Return the string for the English locale as default."""
        return self.strings.get(LocaleType.EN, "")

    def to_json(self) -> dict:
        """Return the localized string as a JSON object."""
        return {loc.value: val for loc, val in self.strings.items()}
