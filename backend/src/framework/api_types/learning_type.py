import sys
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString


class AvailableLearningTypes(Enum):
    """Enumeration of available learning types.

    This enum lists all available learning types for the application.

    Args:
        ...

    Returns:
        None

    """

    FEELING = "FEELING"
    SENSING = "SENSING"
    INTUITIVE = "INTUITIVE"
    THINKING = "THINKING"


class LearningTypeModel(BaseModel):
    """Represents a learning type model.

    This class is used to define a learning type, including its ID, name, and
    description.

    Args:
        id (str): The unique identifier for the learning type.
        name (str): The name of the learning type.
        description (str): The description of the learning type.

    Returns:
        None

    """

    id: AvailableLearningTypes
    title: dict[LocaleType, str]
    short_description: dict[LocaleType, str]
    long_description: dict[LocaleType, str]

    def __str__(self) -> str:
        """Return the string representation of the learning type."""
        return self.id.value


class LearningTypesResponseModel(BaseModel):
    """Model for the available learning types."""

    learning_types: list[LearningTypeModel]


class LearningTypes(Enum):
    """Enumeration of learning type models.

    This enum maps learning type IDs to their corresponding models.

    Args:
        ...

    Returns:
        None

    """

    FEELING = LearningTypeModel(
        id=AvailableLearningTypes.FEELING,
        title=LocalizedString("Feeling", "Feeling").to_json(),
        short_description=LocalizedString(
            "This person prefers: empathy, collaboration, values, personal connection, storytelling.",
            "Diese Person orientiert sich an: Empathie, Zusammenarbeit, Werten, persönlicher Verbindung, Geschichten.",
        ).to_json(),
        long_description=LocalizedString(
            """Is it possible that you are a feeling learner? 

Feeling learners prefer to start with theory before applying it and prefer a human-centered approach to topics. They make decisions based on personal values and the impact on other people. These learners value self-involvement and collaboration, and appreciate a positive and optimistic attitude. 

- Do you like stories or personal anecdotes? 
- Do you think it's good if you can also help and support others? 
- Is it important to you that what you learn is meaningful? 

There's a good chance that you're a feeling learner!""",
            """Wäre es möglich dass du den Feeling Lernstil magst? 

Personen des Feeling-Lernstils beginnen lieber mit der Theorie, bevor sie diese anwenden, und bevorzugen einen menschenzentrierten Ansatz bei den Themen. Sie treffen Entscheidungen basierend auf persönlichen Werten und den Auswirkungen auf andere Menschen. Diese Lernenden schätzen Selbstbeteiligung und Zusammenarbeit, schätzen eine positive und optimistische Einstellung. 

- Magst du Geschichten oder persönliche Anekdoten? 
- Findest du es gut, wenn du auch andere voranbringen und unterstützen kannst? 
- Ist es dir wichtig, dass das was du lernst auch von Bedeutung ist? 

Die Wahrscheinlichkeit ist hoch, dass du den Feeling Lernstil magst!""",
        ).to_json(),
    )

    SENSING = LearningTypeModel(
        id=AvailableLearningTypes.SENSING,
        title=LocalizedString("Sensing", "Sensing").to_json(),
        short_description=LocalizedString(
            "This person prefers: practicality, structure, real-world examples, step-by-step methods, concrete facts.",
            "Diese Person legt Wert auf: Praktikabilität, Struktur, reale Beispiele, schrittweise Methoden, konkrete Fakten.",
        ).to_json(),
        long_description=LocalizedString(
            """Are you a sensing learner?

This learning style prefers to start with practical applications before moving on to theory. These individuals value structure, follow agendas or guidelines and learn best with step-by-step methods. They often rely on past experiences and proven approaches to problem solving. 

- Are concrete facts and realistic scenarios important to you? 
- Do you appreciate precise tasks and clear, actionable suggestions? 
- Do you like practical information more than abstract theories? 

Then you're probably a sensing learner!""",
            """Bist du ein Sensing-Lernender?

Dieser Lernstil bevorzugt es, mit praktischen Anwendungen zu beginnen bevor man sich der Theorie widmet. Diese Personen legen Wert auf Struktur, folgen Agenden oder Richtlinien und lernen am besten mit schrittweisen Methoden. Sie verlassen sich oft auf vergangene Erfahrungen und bewährte Ansätze der Problemlösung. 

- Sind dir konkrete Fakten und realistische Szenarien wichtig? 
- Schätzt du präzise Aufgaben und klare, umsetzbare Vorschläge? 
- Magst du praktische Informationen mehr als abstrakte Theorien? 

Dann lernst du wahrscheinlich anhand des Sensing Lernstils!""",
        ).to_json(),
    )

    INTUITIVE = LearningTypeModel(
        id=AvailableLearningTypes.INTUITIVE,
        title=LocalizedString("Intuitive", "Intuitive").to_json(),
        short_description=LocalizedString(
            "This person prefers: theory, creativity, abstract tasks, independence, conceptual links.",
            "Diese Person schätzt: Theorie, Kreativität, abstrakte Aufgaben, Unabhängigkeit, konzeptionelle Verbindungen.",
        ).to_json(),
        long_description=LocalizedString(
            """Or are you an intuitive learner? 

For this learning style, the focus is first on theory and concepts, and then on connections, patterns or contexts. These learners prefer unstructured activities with choices and prefer self-directed learning and independent work. They thrive on solving new, complex problems using knowledge from the course and critically analyzing new ideas. 

- Do you like creative, abstract tasks? 
- Do you like learning new skills and using your imagination? 
- Do you like varied exercises? 

Then you're probably more of an intuitive learner!""",
            """Oder gefällt dir der Intuitive Lernstil? 

Für diesen Lernstil liegt der Fokus zuerst auf Theorie und Konzepten, danach widmet diese Person sich Verbindungen, Mustern oder Zusammenhängen. Diese Lernenden bevorzugen unstrukturierte Aktivitäten mit Wahlmöglichkeiten und ziehen selbstständiges Lernen und unabhängiges Arbeiten vor. Sie gedeihen bei der Lösung neuer, komplexer Probleme mit dem Wissen aus dem Kurs und der kritischen Analyse neuer Ideen. 

- Magst du kreative, abstrakte Aufgaben? 
- Lernst du gern neue Fähigkeiten und nutzt deine Fantasie? 
- Magst du abwechslungsreiche Übungen? 

Dann willst du wahrscheinlich eher den Intuitive Lernstil!""",
        ).to_json(),
    )

    THINKING = LearningTypeModel(
        id=AvailableLearningTypes.THINKING,
        title=LocalizedString("Thinking", "Thinking").to_json(),
        short_description=LocalizedString(
            "This person prefers: logic, structure, objectives, facts, rationality.",
            "Diese Person setzt auf: Logik, Struktur, Ziele, Fakten, Rationalität.",
        ).to_json(),
        long_description=LocalizedString(
            """Could you be a thinking learner? 

These people prefer to start with theory and use it to solve practical tasks. Thinking learners appreciate logically structured topics with clear goals, outcomes and objectives. These learners value concrete information and rational foundations and make decisions objectively, based on facts, logic and principles. 

- Do you like scheduled measurements of your progress? 
- Are you happy when you can tick off tasks? 
- Do you like fact-based, realistic examples more than flowery stories? 

You'll probably be a thinking learner!""",
            """Könntest du den Thinking-Lernstil präferieren? 

Diese Personen bevorzugen es mit der Theorie zu beginnen und diese zu Lösung praktischer Aufgaben zu nutzen. Thinking-Lernstil schätzen logisch strukturierte Themen mit klaren Zielen, Ergebnissen und Vorgaben. Diese Lernenden legen Wert auf konkrete Informationen und rationale Grundlagen und treffen Entscheidungen objektiv, basierend auf Fakten, Logik und Prinzipien. 

- Magst du geplante Messungen deines Fortschritts? 
- Freust du dich wenn du Aufgaben abhaken kannst? 
- Magst du faktenbasierte, realistische Beispiele mehr als blumige Erzählungen? 

Da wirst du wahrscheinlich den Thinking-Lernstil mögen!""",
        ).to_json(),
    )


def learning_type_for_id(lt_id: AvailableLearningTypes) -> LearningTypeModel:
    """Get the learning type for the given ID."""
    if lt_id not in LearningTypes.__members__:
        raise ValueError(f"Invalid learning type ID: {lt_id}")
    return LearningTypes[lt_id].value


class PersonalityType(Enum):
    """Enumeration of the 16 personality types."""
    
    ISTJ = "ISTJ"
    ISFJ = "ISFJ"
    ESTP = "ESTP"
    ESFP = "ESFP"
    INFJ = "INFJ"
    INTJ = "INTJ"
    ENFP = "ENFP"
    ENTP = "ENTP"
    ISTP = "ISTP"
    INTP = "INTP"
    ESTJ = "ESTJ"
    ENTJ = "ENTJ"
    ISFP = "ISFP"
    INFP = "INFP"
    ESFJ = "ESFJ"
    ENFJ = "ENFJ"


class PersonalityTypeConversionResponse(BaseModel):
    """Response model for personality type conversion."""
    
    learning_type: AvailableLearningTypes
