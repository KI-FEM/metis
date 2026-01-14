from typing import List, Union

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict

from bots.study.helpers.helpers import merge_context, replace_tools
from framework.api_types.request_format import RequestModel
from framework.api_types.response_format import BaseResponseModel

Correctness = Annotated[
    float,
    ...,
    Field(
        ge=0.0,
        le=1.0,
        description=(
            "A float value between 0.0 and 1.0 indicating the "
            "correctness of the answer."
        ),
    ),
]


class QuizQuestionAnswerDict(TypedDict):
    """The format of the quiz question answer in dictionary form."""

    id: Annotated[
        int,
        ...,
        "The unique identifier for the answer.",
    ]
    label: Annotated[
        str,
        ...,
        "The text of the answer option.",
    ]
    correct: Annotated[
        bool,
        ...,
        "Indicates whether this answer is correct.",
    ]


class QuizFeedbackResponseDict(TypedDict):
    """The format of the response to the quiz feedback in dictionary form."""

    user_feedback: Annotated[
        str,
        ...,
        (
            "Feedback provided to the user after completing the quiz helping them to "
            "improve."
        ),
    ]


class BaseQuestionDict(TypedDict):
    """TypedDict for the base question fields."""

    id: Annotated[int, ..., "The unique identifier for the question."]
    title: Annotated[str, ..., "The title of the question."]
    text: Annotated[
        str, ..., "The text displayed for the question, i.e. the question itself."
    ]
    type: Annotated[str, ..., "The type of the question."]
    learning_unit: Annotated[
        str, ..., "The code of the learning unit associated with the question."
    ]


class SingleChoiceQuestionDict(BaseQuestionDict):
    """TypedDict for a single-choice question."""

    options: List[QuizQuestionAnswerDict]
    hint: str


class MultipleChoiceQuestionDict(BaseQuestionDict):
    """TypedDict for a multiple-choice question."""

    options: List[str]
    correct_answer: Annotated[
        str, ..., "The exact string of the correct answer in options."
    ]
    hint: str


class SliderQuestionDict(BaseQuestionDict):
    """TypedDict for a slider question."""

    min: int
    max: int
    step: int
    hint: str
    correct_answer: Annotated[int, ..., "The correct step between min and max."]


class TextQuestionDict(BaseQuestionDict):
    """TypedDict for a free-text question."""

    placeholder: Annotated[
        str, ..., "The placeholder text shown to the user in the answer input field."
    ]
    hint: str
    correct_answer: Annotated[str, ..., "The correct answer text."]


class FillInTheBlanksQuestionDict(BaseQuestionDict):
    """TypedDict for a fill-in-the-blanks question."""

    template: str
    correct_answer: Annotated[
        List[str], ..., "The list of correct answers to the blanks."
    ]
    hint: str


class QuizModelDict(TypedDict):
    """The dictionary format of the quiz, supporting multiple question types."""

    title: Annotated[
        str,
        ...,
        "The title of the quiz.",
    ]
    description: Annotated[
        str,
        ...,
        "The description of the quiz.",
    ]
    questions: Annotated[
        List[
            Union[
                MultipleChoiceQuestionDict,
                SliderQuestionDict,
                TextQuestionDict,
                FillInTheBlanksQuestionDict,
            ]
        ],
        ...,
        "The list of questions in the quiz, which can be of different types.",
    ]


class InspirationsResponse(BaseResponseModel):
    """The format of the response to get inspirations."""

    messages: list[str]
    storage: dict[str, str] = {}


class InspirationsDict(BaseModel):
    """Structure for generated inspirations."""

    questions: list[str]


class Feedback(BaseModel):
    """The format of the feedback."""

    learning_type_rating: int
    comment: str


class FeedbackRequest(RequestModel):
    """The format of the feedback request."""

    feedback: Feedback


class PlanResponse(BaseResponseModel):
    """The format of the response to plan the next session."""

    recommended_topics: list[str]
    recommended_date: str
    storage: dict[str, str] = {}


class PlanResponseDict(TypedDict):
    """The format of the response to plan the next session in dictionary form."""

    topics: Annotated[
        List[str],
        ...,
        "List of recommended topics for the next session.",
    ]


class CitedAnswer(BaseModel):
    """Answer the query based only on the given sources, and cite the sources."""

    answer: str = Field(
        ...,
        description=(
            "The answer to the user question, which is based only on the given sources."
        ),
    )
    citations: List[int] = Field(
        ...,
        description="The integer IDs of the SPECIFIC sources which justify the answer.",
    )


class CitedAnswerDict(TypedDict):
    """Answer the query based only on the given sources, and cite the sources."""

    answer: Annotated[
        str,
        ...,
        "The answer to the user question, which is based only on the given sources.",
    ]
    citations: Annotated[
        List[int],
        ...,
        "The integer IDs of the SPECIFIC sources which justify the answer.",
    ]


class IntroductionDict(TypedDict):
    """The format of the introduction in dictionary form."""

    introduction: Annotated[
        str,
        ...,
        "A short introduction into the selected topic.",
    ]


class StudyBotState(TypedDict):
    """The state of the StudyBot Graph. Contains all messages."""

    messages: Annotated[list, add_messages]
    context: Annotated[list, merge_context]


class StudyBotPostState(TypedDict):
    """The state of the StudyBot Graph after formulating a response.

    Contains all messages and the available tools.
    """

    messages: Annotated[list, add_messages]
    tools: Annotated[list[str], replace_tools]
