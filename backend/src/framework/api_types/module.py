from pydantic import BaseModel

from framework.api_types.locale_type import LocaleType


class Module(BaseModel):
    """Represents a simple module of a topic.
    
    This class is used to define a module, including its ID and title.
    In contrast to the Skill class, this class does not have multiple levels.
    
    Args:
        id (str): The unique identifier for the module.
        title (dict): The localized titles for the module.
        
    Returns:
        None
        
    """

    id: str
    title: dict[LocaleType, str]

class ModulesResponse(BaseModel):
    """A Response model for retrieving multiple modules.
    
    This model is used to return a list of modules.
    
    Args:
        modules (list[Module]): A list of modules.
        
    Returns:
        None
        
    """

    modules: list[Module]

class SkillLevel(BaseModel):
    """Represents a skill level.
    
    This class is used to define a skill level, including its ID, title,
    description, and learning goals.
    
    Args:
        id (str): The unique identifier for the skill level.
        title (dict): The localized titles for the skill level.
        description (dict): The localized descriptions for the skill level.
        learning_goals (dict): The localized learning goals for the skill level.

    Returns:
        None

    """

    id: str
    title: dict[LocaleType, str]
    description: dict[LocaleType, str]
    learning_goals: dict[LocaleType, str]

class Skill(Module):
    """Represents a skill of a topic in the learning system.

    This class is used to define a skill, including its ID, title, description,
    and available levels.

    Args:
        id (str): The unique identifier for the skill.
        title (dict): The localized titles for the skill.
        description (dict): The localized descriptions for the skill.
        levels (list): The list of levels for the skill.
        image (str): The URL of the image representing the skill.

    Returns:
        None

    """

    levels: list[SkillLevel]
    description: dict[LocaleType, str]
    image: str = ""