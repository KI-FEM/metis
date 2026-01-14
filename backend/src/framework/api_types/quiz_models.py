from enum import Enum
from typing import Annotated, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field

from framework.api_types.request_format import RequestModel
from framework.api_types.response_format import BaseResponseModel, Response


class QuizType(str, Enum):
    """Enum for the available quiz types."""

    MULTIPLE_CHOICE = "multiple-choice"
    SLIDER = "slider"
    FREETEXT = "free-text"
    FILL_IN_BLANKS = "fill-in-the-blanks"


class BaseQuestion(BaseModel):
    """A base model containing fields common to all question types."""

    id: int
    title: str
    text: str
    type: QuizType
    score: Tuple[int, int]
    hint: str
    learning_unit: str
    answered: bool = False
    feedback: Optional[str] = None
    is_correct: Optional[bool] = None


class QuizQuestionAnswer(BaseModel):
    """The format of the quiz question answer (for single-choice questions)."""

    id: int
    label: str
    correct: bool = (
        False  # TODO: convert bool to Correctness, as answers can be partially correct
    )


class MultipleChoiceQuestion(BaseQuestion):
    """The format for a multiple-choice question."""

    type: Literal[QuizType.MULTIPLE_CHOICE] = QuizType.MULTIPLE_CHOICE
    options: List[str]
    solution: List[int]
    answer: Optional[List[int]] = None


class SliderQuestion(BaseQuestion):
    """The format for a slider question."""

    type: Literal[QuizType.SLIDER] = QuizType.SLIDER
    min: int
    max: int
    step: int
    solution: int
    answer: Optional[int] = None


class TextQuestion(BaseQuestion):
    """The format for a free-text question."""

    type: Literal[QuizType.FREETEXT] = QuizType.FREETEXT
    placeholder: str
    solution: str
    answer: Optional[str] = None


class FillInTheBlanksQuestion(BaseQuestion):
    """The format for a fill-in-the-blanks question."""

    type: Literal[QuizType.FILL_IN_BLANKS] = QuizType.FILL_IN_BLANKS
    template: str
    solution: List[str]
    answer: Optional[List[str]] = None


AnyQuestion = Annotated[
    Union[
        MultipleChoiceQuestion,
        SliderQuestion,
        TextQuestion,
        FillInTheBlanksQuestion,
    ],
    Field(discriminator="type"),
]


class QuizModel(BaseResponseModel):
    """The format of the quiz, now supporting multiple question types."""

    id: str
    title: str
    description: str
    questions: List[AnyQuestion]
    completed: bool = False
    score: Tuple[int, int]  # [scored, maxPoints]


class InitialQuizModel(QuizModel):
    """The format of the initial quiz."""

    quiz_questions_asked_per_level: tuple[int, int, int]


class QuizAnswers(BaseModel):
    """The format of the request to submit the answers to the test."""

    question_id: int
    selected_options_ids: list[int]


class QuizAnswersRequest(RequestModel):
    """The format of the request to submit the answers to the test."""

    questions: list[AnyQuestion]
    answers: list[QuizAnswers]


class InitialQuizAnswersRequest(RequestModel):
    """The format of the request to submit the answers to the initial quiz."""

    correct_question_ids: list[int]
    questions_asked_per_level: tuple[int, int, int]


class InitialQuizAnswersRecommendation(BaseResponseModel):
    """The format of the recommendation based on the initial quiz answers."""

    quiz_performance_below: int
    quiz_performance_at_level: int
    quiz_performance_above: int
    quiz_recommended_change: int


class QuizFeedbackResponse(BaseResponseModel):
    """The format of the response to the quiz feedback."""

    user_feedback: str


class QuizQuestionEvaluationRequest(RequestModel):
    """The format of the request to evaluate a single quiz question answer."""

    question: AnyQuestion
    user_answer: Union[
        str, int, List[str], List[int]
    ]  # Can be text, slider value, list for blanks, or list for multiple-choice


class QuizQuestionEvaluationResponse(BaseResponseModel):
    """The format of the response for a single quiz question evaluation."""

    score: int  # Points earned
    max_score: int  # Maximum possible points
    is_correct: bool  # Whether the answer is correct
    solution: Union[
        str, int, List[str], List[int]
    ]  # The correct answer/solution
    feedback: str  # Feedback message for the user
    storage: dict[str, str] = {}


class QuizCompletionRequest(RequestModel):
    """The format of the request to complete the quiz."""

    quiz: QuizModel


class QuizCompletionResponse(Response):
    """The format of the response for completing the quiz."""

    events: List[dict]
