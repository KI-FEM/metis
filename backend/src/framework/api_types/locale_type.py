from enum import Enum


class LocaleType(Enum):
    """Represents supported locale types.

    This enum is used to define the supported locales for the application, such as
    English and German.

    Args:
        EN: English locale.
        DE: German locale.

    Returns:
        None

    """

    EN = "en"
    DE = "de"
