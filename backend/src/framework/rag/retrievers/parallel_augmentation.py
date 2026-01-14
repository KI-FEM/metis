# pragma: exclude file
"""Parallel Document Augmentation with Rate Limiting.

This module provides parallel processing of document augmentation tasks with
configurable rate limiting per LLM model.

Rate Limiting Configuration:
---------------------------

You can configure rate limits per model in several ways:

1. Initialize with custom limits:
   model_limits = {
       "gpt-4": {"requests_per_minute": 100, "requests_per_hour": 2000},
       "claude-3.5-sonnet": {"requests_per_minute": 50, "requests_per_hour": 1000}
   }
   rate_limiter = RateLimiter(model_limits)

2. Update limits after initialization:
   rate_limiter.update_model_limits({
       "new-model": {"requests_per_minute": 30, "requests_per_hour": 500}
   })

3. Set individual model limits:
   rate_limiter.set_model_limit("specific-model", 10, 200)

Models not specified will use the default global limits (60/min, 1000/hour).
"""

import asyncio
import json
import logging
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from typing_extensions import Annotated, TypedDict

console = Console()

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True, show_path=False, markup=True)
    ],
)
logger = logging.getLogger(__name__)


MAX_REQUESTS_PER_LLM_PER_MINUTE = 60
MAX_REQUESTS_PER_LLM_PER_HOUR = 1000


class RateLimiter:
    """Rate limiter to track and enforce LLM request limits."""

    def __init__(self, model_limits: Optional[dict] = None):
        """Initialize the rate limiter with empty request tracking.

        Args:
            model_limits: Dict mapping model names to their rate limits.
                         Format: {
                             "model_name": {
                                 "requests_per_minute": int,
                                 "requests_per_hour": int
                             }
                         }
                         If not provided, uses global defaults.

        """
        # Track request timestamps for each LLM model
        self.request_times = defaultdict(deque)
        self.lock = asyncio.Lock()

        # Model-specific rate limits
        self.model_limits = model_limits or {}

        # Default limits for models not specified
        self.default_limits = {
            "requests_per_minute": MAX_REQUESTS_PER_LLM_PER_MINUTE,
            "requests_per_hour": MAX_REQUESTS_PER_LLM_PER_HOUR,
        }

    def get_model_limits(self, llm_model_name: str) -> dict:
        """Get rate limits for a specific model."""
        if llm_model_name in self.model_limits:
            return self.model_limits[llm_model_name]
        return self.default_limits

    async def wait_if_needed(self, llm_model_name: str):
        """Wait if necessary to respect rate limits for the given LLM model."""
        async with self.lock:
            current_time = time.time()
            request_queue = self.request_times[llm_model_name]

            # Get model-specific limits
            limits = self.get_model_limits(llm_model_name)
            max_per_minute = limits["requests_per_minute"]
            max_per_hour = limits["requests_per_hour"]

            # Remove requests older than 1 hour
            while request_queue and current_time - request_queue[0] > 3600:
                request_queue.popleft()

            # Remove requests older than 1 minute for minute limit check
            minute_requests = deque()
            for req_time in request_queue:
                if current_time - req_time <= 60:
                    minute_requests.append(req_time)

            # Check minute limit
            if len(minute_requests) >= max_per_minute:
                oldest_minute_req = minute_requests[0]
                wait_time = 61 - (current_time - oldest_minute_req)
                if wait_time > 0:
                    logger.info(
                        f":timer_clock: Rate limit reached for [bold]{llm_model_name}[/bold]. "
                        f"Waiting [yellow]{wait_time:.1f}s[/yellow] for minute limit "
                        f"({len(minute_requests)}/{max_per_minute})"
                    )
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            # Check hour limit
            if len(request_queue) >= max_per_hour:
                oldest_hour_req = request_queue[0]
                wait_time = 3601 - (current_time - oldest_hour_req)
                if wait_time > 0:
                    logger.info(
                        f":timer_clock: Rate limit reached for [bold]{llm_model_name}[/bold]. "
                        f"Waiting [yellow]{wait_time:.1f}s[/yellow] for hour limit "
                        f"({len(request_queue)}/{max_per_hour})"
                    )
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            # Record this request
            request_queue.append(current_time)

    def get_stats(self, llm_model_name: str) -> dict:
        """Get current rate limit statistics for an LLM model."""
        current_time = time.time()
        request_queue = self.request_times[llm_model_name]

        # Get model-specific limits
        limits = self.get_model_limits(llm_model_name)

        # Count requests in last minute and hour
        minute_count = sum(1 for t in request_queue if current_time - t <= 60)
        hour_count = len(request_queue)

        return {
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "minute_limit": limits["requests_per_minute"],
            "hour_limit": limits["requests_per_hour"],
        }

    def update_model_limits(self, model_limits: dict):
        """Update rate limits for specific models.

        Args:
            model_limits: Dict mapping model names to their rate limits.
                         Format: {
                             "model_name": {
                                 "requests_per_minute": int,
                                 "requests_per_hour": int
                             }
                         }

        """
        self.model_limits.update(model_limits)

    def set_model_limit(
        self, model_name: str, requests_per_minute: int, requests_per_hour: int
    ):
        """Set rate limits for a specific model.

        Args:
            model_name: Name of the model
            requests_per_minute: Maximum requests per minute for this model
            requests_per_hour: Maximum requests per hour for this model

        """
        self.model_limits[model_name] = {
            "requests_per_minute": requests_per_minute,
            "requests_per_hour": requests_per_hour,
        }


# Global rate limiter instance
rate_limiter = RateLimiter(
    {
        "meta-llama/Llama-3.3-70B-Instruct": {
            "requests_per_minute": 100,
            "requests_per_hour": 2000,
        },
        "llama-3.1-8b": {"requests_per_minute": 40, "requests_per_hour": 400},
        "llama-3.3": {"requests_per_minute": 30, "requests_per_hour": 500},
        "gemini-2.5-flash": {"requests_per_minute": 8, "requests_per_hour": 100},
        "gemma-3-27b-it": {"requests_per_minute": 30, "requests_per_hour": 600},
    }
)


def clean_and_filter_questions(questions: list[str]) -> list[str]:
    """Cleans and filters a list of questions.

    Args:
        questions (list[str]): A list of questions to be cleaned and filtered.

    Returns:
        List[str]: A list of cleaned and filtered questions that end with a question mark.

    """
    cleaned_questions = []
    for question in questions:
        cleaned_question = re.sub(r"^\d+\.\s*", "", question.strip())
        if cleaned_question.endswith("?"):
            cleaned_questions.append(cleaned_question)
    return cleaned_questions


class QuestionList(TypedDict):
    """Represents a list of questions generated from a document or fragment."""

    question_list: Annotated[
        list[str], ..., "List of questions generated for the document or fragment"
    ]


class BaseAugmentationTask:
    """Represents a base task for augmentation."""

    fragment: Document
    doc_index: int
    fragment_index: int
    original_doc: Document
    worker_class: str = "BaseParallelAugmentationWorker"


class BaseAugmentationResult:
    """Represents the base result of an augmentation task."""

    task: BaseAugmentationTask
    success: bool
    error: Optional[str] = None


@dataclass
class QuestionAugmentationTask(BaseAugmentationTask):
    """Represents a task for question generation."""

    fragment: Document
    doc_index: int
    fragment_index: int
    original_doc: Document
    questions_per_header: int
    worker_class: str = "QuestionParallelAugmentationWorker"


@dataclass
class QuestionAugmentationResult(BaseAugmentationResult):
    """Represents the result of question generation."""

    task: BaseAugmentationTask
    questions: list[str]
    success: bool
    error: Optional[str] = None


@dataclass
class SummaryAugmentationTask(BaseAugmentationTask):
    """Represents a task for summary generation."""

    fragment: Document
    doc_index: int
    fragment_index: int
    original_doc: Document
    summary_length: int
    worker_class: str = "SummaryParallelAugmentationWorker"


@dataclass
class SummaryAugmentationResult(BaseAugmentationResult):
    """Represents the result of summary generation."""

    task: BaseAugmentationTask
    summary: str
    success: bool
    error: Optional[str] = None


def build_chain(llm: ChatOpenAI):
    """Builds a question generation chain using the provided LLM."""
    prompt = PromptTemplate(
        input_variables=["context", "num_questions"],
        template="Using the context data: {context}\n\nGenerate a list of at least {num_questions} "
        "possible questions that can be asked about this context in the target language. Ensure the questions are "
        "directly answerable within the context and do not include any answers or headers. "
        "Separate the questions with a new line character.",
    )
    chain = prompt | llm.with_structured_output(QuestionList)
    return chain


async def generate_questions(text: str, num_questions: int, llm) -> list[str]:
    """Generates a list of questions based on the provided text.

    Args:
        text (str): The context data from which questions are generated.
        num_questions (int): The number of questions to generate.
        llm: The language model to use for question generation.

    Returns:
        list[str]: A list of unique, filtered questions.

    """
    chain = build_chain(llm)
    input_data = {"context": text, "num_questions": num_questions}
    try:
        result: QuestionList = await chain.ainvoke(input_data)
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return []

    # Extract the list of questions from the QuestionList object
    questions = result["question_list"]

    filtered_questions = clean_and_filter_questions(questions)
    return list(set(filtered_questions))


async def generate_summary(text: str, llm: ChatOpenAI) -> str:
    """Generates a summary of the provided text using the specified LLM.

    Args:
        text (str): The text to summarize.
        llm: The language model to use for summarization.

    Returns:
        str: The generated summary.

    """
    prompt = PromptTemplate(
        input_variables=["context"],
        template="Summarize the following content in a concise manner. You will begin your response with 'Summary:'\n\n{context}",
    )
    chain = prompt | llm | StrOutputParser()

    try:
        summary = await chain.ainvoke({"context": text})
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return ""


class WorkerRegistry:
    """Registry for worker classes to enable clean factory pattern."""

    _workers = {}

    @classmethod
    def register(cls, task_type: str):
        """Decorator to register a worker class for a specific task type."""

        def decorator(worker_class):
            cls._workers[task_type] = worker_class
            return worker_class

        return decorator

    @classmethod
    def get_worker_class(cls, task_type: str):
        """Get the worker class for a given task type."""
        return cls._workers.get(task_type, BaseParallelAugmentationWorker)

    @classmethod
    def get_registered_types(cls):
        """Get all registered task types."""
        return list(cls._workers.keys())


class BaseParallelAugmentationWorker:
    """Base worker class for processing augmentation tasks in parallel."""

    def __init__(self, worker_id: str, llm, fallback_llm):
        """Initialize the worker with an ID, LLM, and fallback LLM."""
        self.worker_id = worker_id
        self.llm = llm
        self.fallback_llm = fallback_llm
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.result_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.failed_tasks = 0
        self.completed_tasks = 0
        self.max_primary_retries = 2
        self.max_fallback_retries = 1
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Max delay in seconds
        self.task_timeout = 30.0  # Maximum time to wait for a single task execution

    async def start(self):
        """Start the worker."""
        self.is_running = True
        asyncio.create_task(self._process_tasks())

    async def stop(self):
        """Stop the worker."""
        self.is_running = False

    async def add_task(self, task: BaseAugmentationTask):
        """Add a task to the worker's queue."""
        await self.task_queue.put(task)

    async def get_result(self) -> Optional[BaseAugmentationResult]:
        """Get a result from the worker if available."""
        try:
            return self.result_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def _process_tasks(self):
        """Main worker loop to process tasks."""
        while self.is_running:
            try:
                # Wait for task with timeout to allow graceful shutdown
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                result = await self._execute_task(task)
                await self.result_queue.put(result)

                if result.success:
                    self.completed_tasks += 1
                else:
                    self.failed_tasks += 1

            except asyncio.TimeoutError:
                continue  # No task available, continue loop
            except Exception as e:
                logger.error(f"Worker {self.worker_id} encountered error: {e}")


@WorkerRegistry.register("QuestionParallelAugmentationWorker")
class QuestionParallelAugmentationWorker(BaseParallelAugmentationWorker):
    """Worker class that processes augmentation tasks using a specific LLM."""

    def __init__(self, worker_id: str, llm, fallback_llm):
        """Initialize the worker with an ID, LLM, and fallback LLM."""
        super().__init__(worker_id, llm, fallback_llm)

    async def _execute_task(
        self, task: QuestionAugmentationTask
    ) -> QuestionAugmentationResult:
        """Execute a single augmentation task with retry logic and timeout."""
        # Primary LLM attempts
        for attempt in range(self.max_primary_retries):
            try:
                logger.debug(
                    f":robot: Worker [bold]{self.worker_id}[/bold] - Processing doc [bold]{task.doc_index}[/bold] "
                    f"fragment [bold]{task.fragment_index}[/bold] (attempt [bold]{attempt + 1}[/bold]) "
                    f"using primary [bold]{_get_model_name(self.llm)}[/bold]"
                )
                await rate_limiter.wait_if_needed(_get_model_name(self.llm))
                questions = await asyncio.wait_for(
                    generate_questions(
                        task.fragment.page_content,
                        task.questions_per_header,
                        self.llm,
                    ),
                    timeout=self.task_timeout,
                )
                if questions:
                    return QuestionAugmentationResult(
                        task=task, questions=questions, success=True
                    )
                raise ValueError("No questions generated")
            except Exception as e:
                logger.warning(
                    f":warning: Worker [bold]{self.worker_id}[/bold] - Primary attempt [bold]{attempt + 1}[/bold] failed: [red]{e}[/red]"
                )
                if attempt < self.max_primary_retries - 1:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)

        # Fallback LLM attempts
        for attempt in range(self.max_fallback_retries):
            try:
                logger.debug(
                    f":robot: Worker [bold]{self.worker_id}[/bold] - Processing doc [bold]{task.doc_index}[/bold] "
                    f"fragment [bold]{task.fragment_index}[/bold] (fallback attempt [bold]{attempt + 1}[/bold]) "
                    f"using fallback [bold]{_get_model_name(self.fallback_llm)}[/bold]"
                )
                await rate_limiter.wait_if_needed(_get_model_name(self.fallback_llm))
                questions = await asyncio.wait_for(
                    generate_questions(
                        task.fragment.page_content,
                        task.questions_per_header,
                        self.fallback_llm,
                    ),
                    timeout=self.task_timeout,
                )
                if questions:
                    return QuestionAugmentationResult(
                        task=task, questions=questions, success=True
                    )
                raise ValueError("No questions generated")
            except Exception as e:
                logger.warning(
                    f":warning: Worker [bold]{self.worker_id}[/bold] - Fallback attempt [bold]{attempt + 1}[/bold] failed: [red]{e}[/red]"
                )
                if attempt < self.max_fallback_retries - 1:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)

        # All attempts failed
        return QuestionAugmentationResult(
            task=task,
            questions=[],
            success=False,
            error=f"Failed after {self.max_primary_retries} primary and {self.max_fallback_retries} fallback attempts",
        )


@WorkerRegistry.register("SummaryParallelAugmentationWorker")
class SummaryParallelAugmentationWorker(BaseParallelAugmentationWorker):
    """Worker class that processes summary tasks using a specific LLM."""

    def __init__(self, worker_id: str, llm, fallback_llm):
        """Initialize the worker with an ID, LLM, and fallback LLM."""
        super().__init__(worker_id, llm, fallback_llm)

    async def _execute_task(
        self, task: SummaryAugmentationTask
    ) -> SummaryAugmentationResult:
        """Execute a single augmentation task with retry logic and timeout."""
        # Primary LLM attempts
        for attempt in range(self.max_primary_retries):
            try:
                logger.debug(
                    f":robot: Worker [bold]{self.worker_id}[/bold] - Processing doc [bold]{task.doc_index}[/bold] "
                    f"fragment [bold]{task.fragment_index}[/bold] (attempt [bold]{attempt + 1}[/bold]) "
                    f"using primary [bold]{_get_model_name(self.llm)}[/bold]"
                )
                await rate_limiter.wait_if_needed(_get_model_name(self.llm))
                summary = await asyncio.wait_for(
                    generate_summary(task.fragment.page_content, self.llm),
                    timeout=self.task_timeout,
                )
                if summary:
                    return SummaryAugmentationResult(
                        task=task, summary=summary, success=True
                    )
                raise ValueError("No summary generated")
            except Exception as e:
                logger.warning(
                    f":warning: Worker [bold]{self.worker_id}[/bold] - Primary attempt [bold]{attempt + 1}[/bold] failed: [red]{e}[/red]"
                )
                if attempt < self.max_primary_retries - 1:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)

        # Fallback LLM attempts
        for attempt in range(self.max_fallback_retries):
            try:
                logger.debug(
                    f":robot: Worker [bold]{self.worker_id}[/bold] - Processing doc [bold]{task.doc_index}[/bold] "
                    f"fragment [bold]{task.fragment_index}[/bold] (fallback attempt [bold]{attempt + 1}[/bold]) "
                    f"using fallback [bold]{_get_model_name(self.fallback_llm)}[/bold]"
                )
                await rate_limiter.wait_if_needed(_get_model_name(self.fallback_llm))
                summary = await asyncio.wait_for(
                    generate_summary(task.fragment.page_content, self.fallback_llm),
                    timeout=self.task_timeout,
                )
                if summary:
                    return SummaryAugmentationResult(
                        task=task, summary=summary, success=True
                    )
                raise ValueError("No summary generated")
            except Exception as e:
                logger.warning(
                    f":warning: Worker [bold]{self.worker_id}[/bold] - Fallback attempt [bold]{attempt + 1}[/bold] failed: [red]{e}[/red]"
                )
                if attempt < self.max_fallback_retries - 1:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)

        # All attempts failed
        return SummaryAugmentationResult(
            task=task,
            summary="",
            success=False,
            error=f"Failed after {self.max_primary_retries} primary and {self.max_fallback_retries} fallback attempts",
        )


def _get_model_name(llm):
    if hasattr(llm, "model_name"):
        return llm.model_name
    elif hasattr(llm, "model"):
        return llm.model
    else:
        return "unknown_model"


class ParallelAugmentationManager:
    """Manages parallel processing of document augmentation tasks."""

    def __init__(self, llms: list, fallback_llm, task_timeout: float = 90.0, show_progress: bool = False):
        """Initialize the manager with a list of LLMs and a fallback LLM.

        Args:
            llms: List of LLM instances to use for parallel processing
            fallback_llm: Fallback LLM to use when primary LLMs fail
            task_timeout: Maximum time in seconds to wait for a single task execution
            show_progress: Whether to show progress bars for tasks

        """
        self.llms = llms
        self.fallback_llm = fallback_llm
        self.task_timeout = task_timeout
        self.workers: list[BaseParallelAugmentationWorker] = []
        self.results_lock = asyncio.Lock()
        self.results: list[BaseAugmentationResult] = []
        self.failed_tasks: list[BaseAugmentationResult] = []
        self.show_progress = show_progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=console,
        ) if show_progress else None

    async def process_fragments(
        self, tasks: list[BaseAugmentationTask]
    ) -> list[BaseAugmentationResult]:
        """Process all augmentation tasks in parallel."""
        if not tasks:
            logger.info(":information: No tasks to process.")
            return []

        num_workers = min(len(tasks), len(self.llms))

        # Determine worker class from first task using registry
        worker_class = WorkerRegistry.get_worker_class(tasks[0].worker_class)

        await self._create_workers(worker_class, num_workers)

        # Distribute tasks
        await self._distribute_tasks(tasks)

        # Collect results
        results = await self._collect_results(len(tasks))

        # Stop workers
        await self._stop_workers()

        # Handle failed tasks
        if self.failed_tasks:
            self._handle_failed_tasks()

        return results

    def _log_rate_limit_stats(self, phase: str):
        """Log current rate limiting statistics for all LLMs."""
        logger.info(f":chart_increasing: [bold]Rate limit statistics - {phase}:[/bold]")

        all_llms = list(self.llms) + [self.fallback_llm]
        for llm in all_llms:
            stats = rate_limiter.get_stats(_get_model_name(llm))
            logger.info(
                f"  :robot: [bold]{_get_model_name(llm)}[/bold]: "
                f"[green]{stats['requests_last_minute']}/{stats['minute_limit']}[/green] requests/min, "
                f"[blue]{stats['requests_last_hour']}/{stats['hour_limit']}[/blue] requests/hour"
            )

    async def _create_workers(
        self, worker_class=QuestionParallelAugmentationWorker, num_workers: int = 0
    ):
        """Create worker instances for each LLM."""
        for i in range(num_workers):
            llm = self.llms[i]
            worker = worker_class(
                worker_id=f"worker_{i}_{_get_model_name(llm)}",
                llm=llm,
                fallback_llm=self.fallback_llm,
            )
            # Set the task timeout for this worker
            worker.task_timeout = self.task_timeout
            self.workers.append(worker)
            await worker.start()

        if self.show_progress:
            logger.info(
                f":rocket: Created [bold]{len(self.workers)}[/bold] workers with [bold]{self.task_timeout}s[/bold] timeout"
            )

    async def _distribute_tasks(self, tasks: list[BaseAugmentationTask]):
        """Distribute tasks evenly among workers."""
        total_tasks = len(tasks)
        if self.show_progress:
            logger.info(
                f":outbox_tray: Distributing [bold]{total_tasks}[/bold] tasks among workers"
            )

        for i, task in enumerate(tasks):
            worker_index = i % len(self.workers)
            await self.workers[worker_index].add_task(task)

    async def _collect_results(
        self, expected_count: int
    ) -> list[BaseAugmentationResult]:
        """Collect results from all workers."""
        collected_results = []
        if self.show_progress:
            with self.progress:
                task_id = self.progress.add_task("Processing fragments", total=expected_count)

        while len(collected_results) < expected_count:
            # Check each worker for results
            for worker in self.workers:
                result = await worker.get_result()
                if result:
                    if not result.success:
                        self.failed_tasks.append(result)
                    collected_results.append(result)
                    if self.show_progress:
                        self.progress.update(task_id, advance=1)

            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)

        return collected_results

    async def _stop_workers(self):
        """Stop all workers."""
        for worker in self.workers:
            await worker.stop()

        if not self.show_progress:
            return
        # Log worker statistics
        logger.info(":bar_chart: [bold]Worker statistics:[/bold]")
        for worker in self.workers:
            logger.info(
                f"  :robot: Worker [bold]{worker.worker_id}[/bold] stats: "
                f"[green]{worker.completed_tasks} completed[/green], "
                f"[red]{worker.failed_tasks} failed[/red]"
            )

    def _handle_failed_tasks(self):
        """Log and save failed tasks."""
        logger.error(
            f":x: [bold red]{len(self.failed_tasks)} tasks failed after all retries.[/bold red]"
        )

        failed_task_data = []
        for result in self.failed_tasks:
            task = result.task
            logger.error(
                f"  - Doc: [bold]{task.doc_index}[/bold], Fragment: [bold]{task.fragment_index}[/bold], Error: [italic]{result.error}[/italic]"
            )
            failed_task_data.append(
                {
                    "doc_index": task.doc_index,
                    "fragment_index": task.fragment_index,
                    "error": result.error,
                    "fragment_content": task.fragment.page_content,
                }
            )

        # Save failed tasks to a file
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        failed_tasks_file = Path(__file__).parent / f"failed_tasks_{now}.json"
        with Path.open(failed_tasks_file, "w") as f:
            json.dump(failed_task_data, f, indent=4)
        logger.info(
            f":floppy_disk: Saved details of failed tasks to [bold]{failed_tasks_file}[/bold]"
        )
