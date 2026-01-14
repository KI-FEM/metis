# pragma: exclude file
import os

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
# Force CPU usage
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, List

from deepeval.metrics import ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from rich.console import Console
from rich.logging import RichHandler

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.llm.deep_eval_lite_llm import DeepEvalLiteLLM
from framework.llm.lite_llm import LiteLLM
from module_loading.evaluation.run_ingesting_methods import (
    SUBDOC_DB_FILE,
    SUBDOC_DB_FILE_AUGMENTED,
    SUBDOC_DB_FILE_SUBDOCS_ONLY,
    SubDocDB,
    read_subdocuments,
)

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

DATA_PATH = Path(Path(__file__).parent.parent.parent / "data").resolve()
DB_FAISS_PATH = Path(
    Path(__file__).parent.parent.parent / "vectorstore/db_faiss"
).resolve()
RETRIEVE_COUNT = 15
RETURN_COUNT = 10
JOB_TIMEOUT = 1800  # 30 minutes

subdoc_db = SubDocDB(subdocuments={})
embeddings = None

deep_eval_model_gemini_light = DeepEvalLiteLLM(
    model_name="gemini-2.5-flash-light", temperature=0
)
deep_eval_model_gemini = DeepEvalLiteLLM(
    model_name="gemini-2.5-flash", temperature=0
)
#deep_eval_model_llama = DeepEvalLiteLLM(model_name="llama3.3", temperature=0)

relevance_metric_gemini = ContextualRelevancyMetric(
    threshold=0.7, model=deep_eval_model_gemini, include_reason=True
)
relevance_metric_llama = ContextualRelevancyMetric(
    threshold=0.7, model=deep_eval_model_gemini_light, include_reason=True
)


def rerank(results: List[Document], scores: List[float], query: str) -> List[Document]:
    return results  # Placeholder for reranking logic


async def retrieve_augmented(query: str) -> list[Document]:
    """Retrieve documents from augmented splits."""
    logger.debug(
        f":mag: Retrieving documents with [bold]Augmented Splits[/bold] for query: [italic]'{query}'[/italic]"
    )

    results: list[Document] = []
    scores: list[float] = []
    vector_store = FAISS.load_local(
        str(Path(DB_FAISS_PATH / "questions")),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retrieved = await vector_store.asimilarity_search_with_relevance_scores(
        query, k=RETRIEVE_COUNT
    )

    for ret in retrieved:
        doc, score = ret
        if doc.metadata["type"] == "ORIGINAL":
            results.append(doc)
            scores.append(score)
        if doc.metadata["type"] == "AUGMENTED":
            og_doc = Document(
                page_content=doc.metadata["text"],
                metadata={
                    **doc.metadata,
                    "type": "ORIGINAL_FROM_AUGMENTED",
                },
            )
            already_i = next(
                (
                    i
                    for i, d in enumerate(results)
                    if d.page_content == og_doc.page_content
                ),
                None,
            )
            if already_i is None:
                results.append(og_doc)
                scores.append(score)
            else:
                if score > scores[already_i]:
                    scores[already_i] = score

    reranked_results = rerank(results, scores, query)
    logger.debug(
        f":arrows_counterclockwise: Reranked [bold]{len(reranked_results)}[/bold] documents with Augmented Splits."
    )

    cut_results = reranked_results[:RETURN_COUNT]
    logger.debug(
        f":page_facing_up: Retrieved [bold]{len(cut_results)}[/bold] documents with Augmented Splits."
    )

    return cut_results


async def retrieve_semantic(query: str) -> list[Document]:
    """Retrieve documents from semantic similarity splits."""
    logger.debug(
        f":mag: Retrieving documents with [bold]Semantic Split[/bold] for query: [italic]'{query}'[/italic]"
    )

    results = []
    scores = []
    vector_store = FAISS.load_local(
        str(Path(DB_FAISS_PATH / "semantic_split")),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retrieved = await vector_store.asimilarity_search_with_relevance_scores(
        query, k=RETRIEVE_COUNT
    )

    for ret in retrieved:
        doc, score = ret
        results.append(doc)
        scores.append(score)

    reranked_results = rerank(results, scores, query)
    logger.debug(
        f":arrows_counterclockwise: Reranked [bold]{len(reranked_results)}[/bold] documents with Semantic Split."
    )

    cut_results = reranked_results[:RETURN_COUNT]
    logger.debug(
        f":page_facing_up: Retrieved [bold]{len(cut_results)}[/bold] documents with Semantic Split."
    )

    return cut_results


async def retrieve_subdoc_augmented(query: str) -> list[Document]:
    """Retrieve documents from subdocument splits."""
    logger.debug(
        f":mag: Retrieving documents with [bold]Subdocument Split[/bold] for query: [italic]'{query}'[/italic]"
    )
    subdoc_db = read_subdocuments(SUBDOC_DB_FILE_AUGMENTED)

    results = []
    scores = []
    vector_store = FAISS.load_local(
        str(Path(DB_FAISS_PATH / "subdocs_augmented")),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retrieved = await vector_store.asimilarity_search_with_relevance_scores(
        query, k=RETRIEVE_COUNT
    )

    sub_doc_list = {}

    for ret in retrieved:
        doc, score = ret
        if "sub_doc_uuid" in doc.metadata:
            if doc.metadata["sub_doc_uuid"] not in subdoc_db.subdocuments:
                logger.warning(
                    f":warning: Subdocument with UUID [bold]{doc.metadata['sub_doc_uuid']}[/bold] not found in subdoc_db."
                )
                results.append(doc)
                scores.append(score)
                continue
            sub_doc = subdoc_db.subdocuments[doc.metadata["sub_doc_uuid"]]
            if doc.metadata["sub_doc_uuid"] not in sub_doc_list:
                sub_doc_list[doc.metadata["sub_doc_uuid"]] = len(results)
                results.append(sub_doc)
                scores.append(score)
            else:
                og_doc_index = sub_doc_list[doc.metadata["sub_doc_uuid"]]
                if score > scores[og_doc_index]:
                    scores[og_doc_index] = score
        else:
            results.append(doc)
            scores.append(score)

    reranked_results = rerank(results, scores, query)
    logger.debug(
        f":arrows_counterclockwise: Reranked [bold]{len(reranked_results)}[/bold] documents with Subdocument Split."
    )

    cut_results = reranked_results[:RETURN_COUNT]
    logger.debug(
        f":page_facing_up: Retrieved [bold]{len(cut_results)}[/bold] documents with Subdocument Split."
    )

    return cut_results


async def retrieve_subdoc_only(query: str) -> list[Document]:
    """Retrieve documents from subdocument splits without augmented data."""
    logger.debug(
        f":mag: Retrieving documents with [bold]Subdocument Split[/bold] for query: [italic]'{query}'[/italic]"
    )
    subdoc_db = read_subdocuments(SUBDOC_DB_FILE_SUBDOCS_ONLY)

    results = []
    scores = []
    vector_store = FAISS.load_local(
        str(Path(DB_FAISS_PATH / "subdocs_only")),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retrieved = await vector_store.asimilarity_search_with_relevance_scores(
        query, k=RETRIEVE_COUNT
    )

    for ret in retrieved:
        doc, score = ret
        results.append(doc)
        scores.append(score)

    reranked_results = rerank(results, scores, query)
    logger.debug(
        f":arrows_counterclockwise: Reranked [bold]{len(reranked_results)}[/bold] documents with Subdocuments Only."
    )

    cut_results = reranked_results[:RETURN_COUNT]
    logger.debug(
        f":page_facing_up: Retrieved [bold]{len(cut_results)}[/bold] documents with Subdocuments Only."
    )

    return cut_results


async def retrieve_subdoc(query: str) -> list[Document]:
    """Retrieve documents from subdocument splits."""
    logger.debug(
        f":mag: Retrieving documents with [bold]Subdocument Split[/bold] for query: [italic]'{query}'[/italic]"
    )
    subdoc_db = read_subdocuments(SUBDOC_DB_FILE)

    results = []
    scores = []
    vector_store = FAISS.load_local(
        str(Path(DB_FAISS_PATH / "subdocs")),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retrieved = await vector_store.asimilarity_search_with_relevance_scores(
        query, k=RETRIEVE_COUNT
    )

    sub_doc_list = {}

    for ret in retrieved:
        doc, score = ret
        if "sub_doc_uuid" in doc.metadata:
            if doc.metadata["sub_doc_uuid"] not in subdoc_db.subdocuments:
                logger.warning(
                    f":warning: Subdocument with UUID [bold]{doc.metadata['sub_doc_uuid']}[/bold] not found in subdoc_db."
                )
                results.append(doc)
                scores.append(score)
                continue
            sub_doc = subdoc_db.subdocuments[doc.metadata["sub_doc_uuid"]]
            if doc.metadata["sub_doc_uuid"] not in sub_doc_list:
                sub_doc_list[doc.metadata["sub_doc_uuid"]] = len(results)
                results.append(sub_doc)
                scores.append(score)
            else:
                og_doc_index = sub_doc_list[doc.metadata["sub_doc_uuid"]]
                if score > scores[og_doc_index]:
                    scores[og_doc_index] = score
        else:
            results.append(doc)
            scores.append(score)

    reranked_results = rerank(results, scores, query)
    logger.debug(
        f":arrows_counterclockwise: Reranked [bold]{len(reranked_results)}[/bold] documents with Subdocument Split."
    )

    cut_results = reranked_results[:RETURN_COUNT]
    logger.debug(
        f":page_facing_up: Retrieved [bold]{len(cut_results)}[/bold] documents with Subdocument Split."
    )

    return cut_results


async def build_case(
    retrieving_func: Callable[[str], Awaitable[list[Document]]],
    question: str,
    gt_answer: str,
    answer_chain,
) -> LLMTestCase | None:
    """Build a test case for evaluation."""
    context = await retrieving_func(question)
    if not context:
        logger.warning(
            f":warning: No context retrieved for question: [italic]'{question}'[/italic]"
        )
        return None

    generated_answer = await answer_chain.ainvoke(
        {
            "context": "\n".join([doc.page_content for doc in context]),
            "question": question,
        }
    )

    return LLMTestCase(
        input=question,
        expected_output=gt_answer,
        actual_output=generated_answer,
        retrieval_context=[doc.page_content for doc in context],
    )


async def evaluate(
    evaluate_subdoc_only: bool = True,
    evaluate_subdoc: bool = True,
    evaluate_semantic: bool = True,
    evaluate_augmented: bool = True,
    evaluate_subdoc_augmented: bool = True,
):
    """Evaluate different retrieval methods in parallel."""
    logger.info(":rocket: Starting evaluation...")

    global embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large-instruct",
        model_kwargs={"device": "cpu"},
    )

    answer_prompt = PromptTemplate.from_template(
        """
    Answer the question based on the provided context.
    
    Context: {context}
    Question: {question}
    """
    )
    answer_chain = (
        answer_prompt
        | LiteLLM(model_name="llama-3.3").llm_chatopenai(temperature=0)
        | StrOutputParser()
    )
    questions = [
        "What factors influence resilience?",
        "Where can I find help to improve my resilience?",
        "How can I improve my resilience?",
        "Is resilience influential to advancements in education?",
        "Does gender influence resilience and in what ways?",
    ]
    gt_answers = [
        "Factors influencing resilience include self-perception, self-efficacy, social competence, self-regulation, problem-solving skills, and active coping skills. Other sources suggest that caring and supportive relationships within and outside family support resilience.",
        "Beyond caring family members and friends, individuals can find help to improve their resilience through self-help and support groups, books, or if necessary a mental health professional.",
        "Improving resilience is an individual process that takes time and effort. It involves making connections, reinterpret negative events, accept change as a part of life, and take decisive actions in adverse situations. It also includes maintaining a hopeful outlook and taking care of oneself.",
        "Resilience is crucial in education as it helps students cope with challenges, adapt to change, and persist in the face of setbacks. However, the importance of resilience for educational advancements is debated, with a study from 2017 being unable to find a significant relationship between resilience and educational advancements.",
        "Studies show that gender has no effect on students' academic resilience. Opportunities for resilience development are equally available. Though, a student's cohort has a significant influence on their resilience, requiring further research to understand the nuances of this relationship.",
    ]

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = Path(__file__).parent / "results" / now
    results_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f":floppy_disk: Writing results to [bold]{results_dir}[/bold]...")
    
    for i, question in enumerate(questions):
        gt_answer = gt_answers[i]
        
        if evaluate_semantic:
            logger.info(f":mag: Evaluating Semantic Split for question: [italic]'{question}'[/italic]")
            case = await build_case(retrieve_semantic, question, gt_answer, answer_chain)
            if case:
                await relevance_metric_gemini.a_measure(case)
                result = {
                    "score": relevance_metric_gemini.score,
                    "reason": relevance_metric_gemini.reason,
                    "question": question,
                }
                with open(results_dir / "results_semantic.jsonl", "a") as f:
                    f.write(json.dumps(result) + "\n")
        if evaluate_subdoc:
            logger.info(f":mag: Evaluating Subdocument Split for question: [italic]'{question}'[/italic]")
            case = await build_case(retrieve_subdoc, question, gt_answer, answer_chain)
            if case:
                await relevance_metric_gemini.a_measure(case)
                result = {
                    "score": relevance_metric_gemini.score,
                    "reason": relevance_metric_gemini.reason,
                    "question": question,
                }
                with open(results_dir / "results_subdoc.jsonl", "a") as f:
                    f.write(json.dumps(result) + "\n")
        if evaluate_subdoc_only:
            logger.info(f":mag: Evaluating Subdocument Only for question: [italic]'{question}'[/italic]")
            case = await build_case(retrieve_subdoc_only, question, gt_answer, answer_chain)
            if case:
                await relevance_metric_gemini.a_measure(case)
                result = {
                    "score": relevance_metric_gemini.score,
                    "reason": relevance_metric_gemini.reason,
                    "question": question,
                }
                with open(results_dir / "results_subdoc_only.jsonl", "a") as f:
                    f.write(json.dumps(result) + "\n")
        if evaluate_augmented:
            logger.info(f":mag: Evaluating Augmented Split for question: [italic]'{question}'[/italic]")
            case = await build_case(retrieve_augmented, question, gt_answer, answer_chain)
            if case:
                await relevance_metric_gemini.a_measure(case)
                result = {
                    "score": relevance_metric_gemini.score,
                    "reason": relevance_metric_gemini.reason,
                    "question": question,
                }
                with open(results_dir / "results_augmented.jsonl", "a") as f:
                    f.write(json.dumps(result) + "\n")
        if evaluate_subdoc_augmented:
            logger.info(f":mag: Evaluating Subdocument Augmented for question: [italic]'{question}'[/italic]")
            case = await build_case(
                retrieve_subdoc_augmented, question, gt_answer, answer_chain
            )
            if case:
                await relevance_metric_gemini.a_measure(case)
                result = {
                    "score": relevance_metric_gemini.score,
                    "reason": relevance_metric_gemini.reason,
                    "question": question,
                }
                with open(results_dir / "results_subdoc_augmented.jsonl", "a") as f:
                    f.write(json.dumps(result) + "\n")
        
    logger.info(":white_check_mark: Evaluation completed.")


async def evaluate_parallel(
    evaluate_subdoc_only: bool = True,
    evaluate_subdoc: bool = True,
    evaluate_semantic: bool = True,
    evaluate_augmented: bool = True,
    evaluate_subdoc_augmented: bool = True,
):
    logger.info(":rocket: Starting evaluation...")

    global embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large-instruct",
        model_kwargs={"device": "cpu"},
    )

    answer_prompt = PromptTemplate.from_template(
        """
    Answer the question based on the provided context.
    
    Context: {context}
    Question: {question}
    """
    )
    answer_chain = (
        answer_prompt
        | LiteLLM(model_name="llama-3.3").llm_chatopenai(temperature=0)
        | StrOutputParser()
    )
    questions = [
        "What factors influence resilience?",
        "Where can I find help to improve my resilience?",
        "How can I improve my resilience?",
        "Is resilience influential to advancements in education?",
        "Does gender influence resilience and in what ways?",
    ]
    gt_answers = [
        "Factors influencing resilience include self-perception, self-efficacy, social competence, self-regulation, problem-solving skills, and active coping skills. Other sources suggest that caring and supportive relationships within and outside family support resilience.",
        "Beyond caring family members and friends, individuals can find help to improve their resilience through self-help and support groups, books, or if necessary a mental health professional.",
        "Improving resilience is an individual process that takes time and effort. It involves making connections, reinterpret negative events, accept change as a part of life, and take decisive actions in adverse situations. It also includes maintaining a hopeful outlook and taking care of oneself.",
        "Resilience is crucial in education as it helps students cope with challenges, adapt to change, and persist in the face of setbacks. However, the importance of resilience for educational advancements is debated, with a study from 2017 being unable to find a significant relationship between resilience and educational advancements.",
        "Studies show that gender has no effect on students' academic resilience. Opportunities for resilience development are equally available. Though, a student's cohort has a significant influence on their resilience, requiring further research to understand the nuances of this relationship.",
    ]

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = Path(__file__).parent / "results" / now
    results_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f":floppy_disk: Writing results to [bold]{results_dir}[/bold]...")

    queue = asyncio.Queue()

    async def worker(
        name: str,
        q: asyncio.Queue,
        primary_metric: ContextualRelevancyMetric,
        secondary_metric: ContextualRelevancyMetric,
    ):
        while True:
            try:
                (
                    retrieval_type,
                    retrieving_func,
                    question,
                    gt_answer,
                    is_retry,
                ) = await q.get()
                
                metric_to_use = secondary_metric if is_retry else primary_metric
                llm_name = "secondary" if is_retry else "primary"
                log_prefix = f"Worker {name} ({llm_name} LLM) for {retrieval_type} on question '{question[:20]}...':"
                
                measurement_task = None
                try:
                    case = await build_case(
                        retrieving_func, question, gt_answer, answer_chain
                    )
                    if not case:
                        logger.warning(f"{log_prefix} No context retrieved, skipping.")
                        q.task_done()
                        continue

                    logger.info(f"{log_prefix} Measuring relevance...")
                    measurement_task = asyncio.create_task(metric_to_use.a_measure(case))
                    await asyncio.wait_for(measurement_task, timeout=JOB_TIMEOUT)

                    if metric_to_use.score is None:
                        raise ValueError("Metric score is None, indicating a possible LLM format error.")

                    result = {"score": metric_to_use.score, "reason": metric_to_use.reason, "question": question}
                    result_file = results_dir / f"results_{retrieval_type}.jsonl"
                    with open(result_file, "a") as f:
                        f.write(json.dumps(result) + "\n")
                    logger.info(f"{log_prefix} Successfully processed and saved.")

                except (asyncio.TimeoutError, ValueError) as e:
                    if measurement_task and not measurement_task.done():
                        measurement_task.cancel()
                        await asyncio.gather(measurement_task, return_exceptions=True)

                    error_type = "Timeout" if isinstance(e, asyncio.TimeoutError) else "Formatting Error"
                    logger.warning(f"{log_prefix} Failed due to {error_type}.")

                    if not is_retry:
                        logger.info(f"{log_prefix} Retrying with other LLM...")
                        await q.put(
                            (
                                retrieval_type,
                                retrieving_func,
                                question,
                                gt_answer,
                                True,
                            )
                        )
                    else:
                        logger.error(f"{log_prefix} Failed after retry. Giving up.")
                        failure_result = {"score": None, "reason": f"Failed due to {error_type} on both LLMs", "question": question}
                        result_file = results_dir / f"results_{retrieval_type}.jsonl"
                        with open(result_file, "a") as f:
                            f.write(json.dumps(failure_result) + "\n")
                
                finally:
                    q.task_done()

            except asyncio.CancelledError:
                logger.info(f"Worker {name} cancelled.")
                break
            except Exception as e:
                logger.error(f"Worker {name} encountered an unexpected error: {e}", exc_info=True)
                q.task_done()

    tasks_to_run = []
    if evaluate_semantic:
        tasks_to_run.append(("semantic", retrieve_semantic))
    if evaluate_subdoc:
        tasks_to_run.append(("subdoc", retrieve_subdoc))
    if evaluate_subdoc_only:
        tasks_to_run.append(("subdoc_only", retrieve_subdoc_only))
    if evaluate_augmented:
        tasks_to_run.append(("augmented", retrieve_augmented))
    if evaluate_subdoc_augmented:
        tasks_to_run.append(("subdoc_augmented", retrieve_subdoc_augmented))

    for i, question in enumerate(questions):
        gt_answer = gt_answers[i]
        for retrieval_type, retrieving_func in tasks_to_run:
            await queue.put(
                (retrieval_type, retrieving_func, question, gt_answer, False)
            )

    worker_tasks = [
        asyncio.create_task(
            worker("gemini", queue, relevance_metric_gemini, relevance_metric_llama)
        ),
        asyncio.create_task(
            worker("gemini-light", queue, relevance_metric_llama, relevance_metric_gemini)
        ),
    ]

    await queue.join()

    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    logger.info(":white_check_mark: Evaluation completed.")


def calculate_averages():
    results_dir = Path(__file__).parent / "results"
    try:
        latest_run_dir = max(
            (d for d in results_dir.iterdir() if d.is_dir()),
            key=os.path.getmtime,
        )
    except ValueError:
        logger.warning(":warning: No result directories found.")
        return

    logger.info(
        f":magnifying_glass_tilted_left: Reading results from [bold]{latest_run_dir}[/bold]"
    )

    results_data = {}
    for file_path in latest_run_dir.glob("*.jsonl"):
        retrieval_type = file_path.stem.replace("results_", "")
        results_data[retrieval_type] = []
        with open(file_path, "r") as f:
            for line in f:
                results_data[retrieval_type].append(json.loads(line))

    def calculate_average(results):
        valid_scores = [r["score"] for r in results if r.get("score") is not None]
        if not valid_scores:
            return 0
        return sum(valid_scores) / len(valid_scores)

    averages = {
        retrieval_type: calculate_average(data)
        for retrieval_type, data in results_data.items()
    }

    for retrieval_type, avg_score in averages.items():
        logger.info(
            f":bar_chart: Average {retrieval_type.replace('_', ' ')} retrieval score: [bold]{avg_score:.4f}[/bold]"
        )

    if not averages:
        logger.warning("No results found to determine a winner.")
        return

    winner = max(averages, key=averages.get)
    logger.info(
        f":trophy: [bold green]{winner.replace('_', ' ').title()} retrieval is the best method![/bold green]"
    )


if __name__ == "__main__":
    asyncio.run(
        evaluate(
            evaluate_subdoc_only=True,
            evaluate_subdoc=True,
            evaluate_semantic=False,
            evaluate_augmented=False,
            evaluate_subdoc_augmented=True,
        )
    )
    calculate_averages()
