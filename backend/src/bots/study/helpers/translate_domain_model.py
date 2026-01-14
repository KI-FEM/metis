import asyncio
import datetime
import logging
import sys
from pathlib import Path
from typing import TypedDict

from langchain.prompts import PromptTemplate
from langchain_core.globals import set_debug
from typing_extensions import Annotated

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.api_types.localized_string import LocalizedString
from framework.db.database import Database
from framework.db.db_types import (
    ConceptTranslationDB,
    LanguageDB,
    LearningUnitCombined,
    LearningUnitTranslationDB,
)
from framework.llm.lite_llm import LiteLLM

logger = logging.getLogger(__name__)
set_debug(True)  # Enable debug mode for LangChain


async def translate_model(idcompetence: int):
    """Translate the domain model for a given competence ID."""
    logger.info(f"Translating domain model for competence ID: {idcompetence}")
    db = Database()
    await db.connect()

    errored_translations = []

    all_learning_units = await db.get_learning_unit_translations_by_competence(
        idcompetence
    )
    lus_per_id = {lu.idlearningunit: lu for lu in all_learning_units}
    languages = await db.get_languages()

    # get all learning units that are not already translated into every language
    languages_of_learning_units = {}

    for learning_unit_id in all_learning_units:
        if learning_unit_id.idlearningunit not in languages_of_learning_units:
            languages_of_learning_units[learning_unit_id.idlearningunit] = []
        languages_of_learning_units[learning_unit_id.idlearningunit].append(
            learning_unit_id.idlanguage
        )

    num_of_languages = len(languages)
    untranslated_unit_ids = [
        lu
        for lu, langs in languages_of_learning_units.items()
        if len(langs) < num_of_languages
    ]

    for learning_unit_id in untranslated_unit_ids:
        # Translate each learning unit
        missing_languages = [
            lang
            for lang in languages
            if lang.idlanguage not in languages_of_learning_units[learning_unit_id]
        ]
        learning_unit = lus_per_id[learning_unit_id]
        for lang in missing_languages:
            try:
                translated = await translate_learning_unit(learning_unit, lang)
                if translated:
                    await db.add_learning_unit_translation(translated)
            except Exception as e:
                logger.error(
                    f"Error translating learning unit {learning_unit_id} to "
                    f"{lang.code}: {e}"
                )
                errored_translations.append((learning_unit, lang.code, str(e)))

    logger.info(f"Translation completed with {len(errored_translations)} errors.")
    if errored_translations:
        logger.error("Errors during translation:")
        for unit_id, lang_code, error in errored_translations:
            logger.error(f"Unit ID: {unit_id}, Language: {lang_code}, Error: {error}")


class LearningUnitTranslationDict(TypedDict):
    """Answer the query based only on the given sources, and cite the sources."""

    learninggoal: Annotated[
        str,
        ...,
        "The learning goal of the learning unit.",
    ]
    task: Annotated[
        str,
        ...,
        "An example task of a learning goal.",
    ]
    solution: Annotated[
        str,
        ...,
        "The solution to task.",
    ]


async def translate_learning_unit(
    learning_unit: LearningUnitTranslationDB, language: LanguageDB
):
    """Translate a learning unit into the specified language."""
    logger.info(
        f"Translating learning unit {learning_unit.idlearningunit} to {language.code}"
    )

    llm = LiteLLM(model_name="llama-4")
    prompt = PromptTemplate(
        template="""
    Translate the following learning unit into {language}:

    Learning Goal: {learninggoal}
    Task: {task}
    Solution: {solution}
    """
    )
    chain = prompt | llm.llm_chatopenai().with_structured_output(
        LearningUnitTranslationDict
    )
    translated = await chain.ainvoke(
        {
            "language": language.code,
            "learninggoal": learning_unit.learninggoal,
            "task": learning_unit.task,
            "solution": learning_unit.solution,
        }
    )

    return LearningUnitTranslationDB(
        idlearningunit=learning_unit.idlearningunit,
        idlanguage=language.idlanguage,
        learninggoal=translated["learninggoal"],
        task=translated["task"],
        solution=translated["solution"],
    )


async def translate_all_concepts():
    """Translate all concepts into English that do not have a translation yet."""
    errored_translations = []
    db = Database()
    await db.connect()
    query = """SELECT * FROM concepttranslation where idconcept NOT IN 
    (select idconcept from concepttranslation where idlanguage=5)"""
    concepts = await db.execute(query)
    logger.info(f"found {len(concepts)} concepts")
    language_en = LanguageDB(
        idlanguage=5,
        code="en",
        name="English",
        createdat=datetime.datetime.now(),
        enabled=True,
    )
    for concept_rows in concepts:
        concept = ConceptTranslationDB(
            idconcept=concept_rows[0],
            idlanguage=concept_rows[1],
            name=concept_rows[2],
            description=concept_rows[3],
        )
        try:
            translated = await translate_concept(concept, language_en)
            if translated:
                await db.add_concept_translation(translated)
        except Exception as e:
            logger.error(
                f"Error translating concept {concept.idconcept} to "
                f"{language_en.code}: {e}"
            )
            errored_translations.append((concept, language_en.code, str(e)))

    logger.info(f"Translation completed with {len(errored_translations)} errors.")
    if errored_translations:
        logger.error("Errors during translation:")
        for concept, lang_code, error in errored_translations:
            logger.error(
                f"Concept ID: {concept.idconcept}, Language: {lang_code}, Er: {error}"
            )


class ConceptTranslationDict(TypedDict):
    """Answer the query based only on the given sources, and cite the sources."""

    name: Annotated[
        str,
        ...,
        "The name of the concept.",
    ]
    description: Annotated[
        str,
        ...,
        "The description of the concept.",
    ]


async def translate_concept(concept: ConceptTranslationDB, language: LanguageDB):
    """Translate the given concept into the given language."""
    logger.info(f"Translating concept {concept.idconcept} to {language.code}")

    llm = LiteLLM(model_name="llama-4")
    prompt = PromptTemplate(
        template="""
    Translate the following concept into {language}:

    Name: {name}
    Description: {description}
    """
    )
    chain = prompt | llm.llm_chatopenai().with_structured_output(ConceptTranslationDict)
    translated = await chain.ainvoke(
        {
            "language": language.code,
            "name": concept.name,
            "description": concept.description,
        }
    )

    return ConceptTranslationDB(
        idconcept=concept.idconcept,
        idlanguage=language.idlanguage,
        name=translated["name"],
        description=translated["description"],
    )


async def generate_lu_codes_and_names():
    """Generate codes and names for all learning units that do not have a code yet."""
    db = Database()
    await db.connect()
    query = """
        SELECT idlearningunit FROM learningunit 
        WHERE code IS NULL OR code = ''
    """
    luids = [row[0] for row in await db.execute(query)]
    learning_units = await db.get_learning_units_joined(luids, LocaleType.EN)
    logger.info(f"found {len(learning_units)} learning units without code")
    errored_translations = []
    for lu in learning_units:
        try:
            (
                generated_code,
                generated_name,
            ) = await generate_code__and_name_for_learning_unit(lu)
            if generated_code:
                await db.update_learning_unit_code(lu.idlearningunit, generated_code)
            if generated_name:
                await db.update_learning_unit_name(lu.idlearningunit, generated_name)
        except Exception as e:
            logger.error(
                f"Error generating code for learning unit {lu.idlearningunit}: {e}"
            )
            errored_translations.append((lu, str(e)))

    logger.info(f"Code generation completed with {len(errored_translations)} errors.")


class LearningUnitCodeDict(TypedDict):
    """Answer the query based only on the given sources, and cite the sources."""

    code: Annotated[
        str,
        ...,
        (
            "A short and unique code for the learning unit, e.g. "
            "'LU_create_resilience_example'.",
        )
    ]
    name_en: Annotated[
        str,
        ...,
        "A name for the learning unit in English.",
    ]
    name_de: Annotated[
        str,
        ...,
        "A name for the learning unit in German.",
    ]


async def generate_code__and_name_for_learning_unit(
    learning_unit: LearningUnitCombined,
):
    """Generate a code and name for the given learning unit."""
    logger.info(
        f"Generating code and name for learning unit {learning_unit.idlearningunit}"
    )

    llm = LiteLLM(model_name="llama-4")
    prompt = PromptTemplate(
        template="""
    Generate a short code (no spaces, only snake case) and names in English and German 
for the following learning unit:

    Learning Goal: {learninggoal}
    
    <example>
    **Input:**
    Learning Goal: Students can critically evaluate the effectiveness of various 
cognitive strategies.
    
    **Output:**
    {{
        "code": "LU_eval_cognitive_strats",
        "name_en": "Evaluate Cognitive Strategies",
        "name_de": "Kognitive Strategien Bewerten"
    }}
    </example>
    
    <example_2>
    **Input:**
    Learning Goal: Students can develop their own training to promote self-efficacy.
    
    **Output:**
    {{
        "code": "LU_dev_SE_training",
        "name_en": "Develop Self-Efficacy Training",
        "name_de": "Training zur Selbstwirksamkeit Entwickeln"
    }}
    """
    )
    chain = prompt | llm.llm_chatopenai().with_structured_output(LearningUnitCodeDict)
    generated = await chain.ainvoke(
        {
            "learninggoal": learning_unit.learning_goal,
        }
    )

    name = LocalizedString(
        en_string=generated["name_en"], de_string=generated["name_de"]
    )
    return generated["code"], name


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.info("Usage: python -m src.importer <competence_id>")
        sys.exit(1)
    competence_id = sys.argv[1]
    asyncio.run(translate_model(competence_id))

    # asyncio.run(translate_ all_concepts())
    # asyncio.run(generate_ lu_codes_and_names())
