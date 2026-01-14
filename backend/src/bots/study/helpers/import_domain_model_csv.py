# pragma: exclude file
import asyncio
import csv
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import aiofiles

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from framework.db.database import Database
from framework.db.db_types import (
    CompetenceConceptDB,
    CompetenceLevelDB,
    CompetenceLevelTranslationDB,
    ConceptDB,
    ConceptTranslationDB,
    LearningStepDB,
    LearningStepTranslationDB,
    LearningUnitDB,
    LearningUnitTranslationDB,
)

logger = logging.getLogger(__name__)

async def import_knowledge_database(
    csv_file_path: str, 
    language_code: str = "de",
    competence_code: str = "resilience"
):
    """Imports a knowledge database from a CSV file into the PostgreSQL database."""
    db = Database()
    await db.connect()

    competence = await db.get_competence_by_code(competence_code)

    try:
        # Get language ID
        language = await db.get_language(language_code)
        if not language:
            logger.info(f"Language '{language_code}' not found in the database.")
            return

        # Get or create a default competence level
        competence_levels = await db.get_competence_levels()
        logger.info("No competence levels found. Creating a default one.")
        default_competence_level_db = CompetenceLevelDB(
            code="default", order=1, enabled=True
        )
        competence_level_id = await db.add_competence_level(
            default_competence_level_db
        )
        default_competence_level_translation_db = CompetenceLevelTranslationDB(
            idcompetencelevel=competence_level_id,
            idlanguage=language.idlanguage,
            name="Default Level",
            description="Default competence level",
        )
        await db.add_competence_level_translation(
            default_competence_level_translation_db
        )

        async with aiofiles.open(csv_file_path, mode="r", encoding="utf-8") as f:
            content = await f.read()
            reader = csv.reader(content.splitlines(), delimiter=";")
            header = next(reader)
            descriptions = next(reader)

            # Import Concepts
            concepts = {}
            for i, concept_name in enumerate(header):
                if i < 2:  # Skip first two columns (empty and "Stufen")
                    continue

                concept_name = concept_name.strip().replace("Konzept ", "")
                if not concept_name:
                    continue

                description = descriptions[i].strip()

                # Create and insert concept
                concept = await db.get_concept_by_code(concept_name)
                if not concept:
                    new_concept = ConceptDB(
                        idconcept=1, 
                        code=concept_name, 
                        createdat=datetime.now(), 
                        enabled=True
                    )
                    concept_id = await db.add_concept(new_concept)
                    concept = ConceptDB(
                        idconcept=concept_id, 
                        code=concept_name, 
                        createdat=datetime.now(), 
                        enabled=True
                    )
                    concept_competence = CompetenceConceptDB(
                        idcompetence=competence.idcompetence,
                        idconcept=concept.idconcept,
                        createdat=datetime.now(),
                        enabled=True,
                    )
                    await db.add_competence_concept(concept_competence)

                concepts[i] = concept

                # Create and insert concept translation
                concept_translation = ConceptTranslationDB(
                    idconcept=concept.idconcept,
                    idlanguage=language.idlanguage,
                    name=concept_name,
                    description=description,
                )
                imported = await db.add_concept_translation(concept_translation)
                if imported:
                    logger.info(f"Imported concept: {concept_name}")

            # Import Learning Units
            learning_units_data = {}
            for row in reader:
                if not any(row) or len(row) < 2:
                    continue

                row_type = row[0].strip()
                stufe = row[1].strip()

                if not stufe:
                    continue

                if row_type == "Lernziel":
                    learning_units_data = {"stufe": stufe, "lernziele": row}
                elif row_type == "Aufgabe":
                    learning_units_data["aufgaben"] = row
                elif row_type == "Lösung":
                    learning_units_data["loesungen"] = row

                    # Now we have a complete learning unit, let's process it
                    for i, col_name in enumerate(header):
                        if i < 2 or i not in concepts:
                            continue

                        concept: ConceptDB = concepts[i]
                        lernziel = learning_units_data["lernziele"][i].strip()
                        aufgabe = learning_units_data["aufgaben"][i].strip()
                        loesung = learning_units_data["loesungen"][i].strip()

                        if not lernziel and not aufgabe and not loesung:
                            continue

                        # Get or create learning step
                        learning_step = await db.get_learning_step_by_name(
                            learning_units_data["stufe"]
                        )
                        if not learning_step:
                            new_learning_step = LearningStepDB(
                                name=learning_units_data["stufe"],
                                order=len(concepts) + 1,
                                enabled=True,
                            )
                            learning_step_id = await db.add_learning_step(
                                new_learning_step
                            )
                            learning_step_translation = LearningStepTranslationDB(
                                idlearningstep=learning_step_id,
                                idlanguage=language.idlanguage,
                                name=learning_units_data["stufe"],
                            )
                            await db.add_learning_step_translation(
                                learning_step_translation
                            )
                            learning_step = LearningStepDB(
                                idlearningstep=learning_step_id,
                                name=learning_units_data["stufe"],
                                order=len(concepts) + 1,
                                enabled=True,
                            )

                        level_id = None
                        match = re.search(r'#(\d+)', lernziel)
                        if match:
                            level_id = int(match.group(1))
                            lernziel = re.sub(r'#\d+', '', lernziel).strip()

                        # Create learning unit
                        new_learning_unit = LearningUnitDB(
                            idlearningunit=1,  # Placeholder ID, will be set by DB
                            idstep=learning_step.idstep,
                            idconcept=concept.idconcept,
                            idcompetencelevel=competence_levels[level_id-1].idcompetencelevel,
                            createdat=datetime.now(), # Placeholder for created at
                            enabled=True, # Placeholder for enabled status
                        )
                        learning_unit_id = await db.add_learning_unit(new_learning_unit)

                        # Create learning unit translation
                        new_learning_unit_translation = LearningUnitTranslationDB(
                            idlearningunit=learning_unit_id,
                            idlanguage=language.idlanguage,
                            learninggoal=lernziel,
                            task=aufgabe,
                            solution=loesung,
                        )
                        await db.add_learning_unit_translation(
                            new_learning_unit_translation
                        )
                        logger.info(
                            "Imported learning unit for concept "
                            f"'{concept.code}' and stufe '{learning_step.code}'"
                        )

    finally:
        await db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.info("Usage: python -m src.importer <path_to_csv_file>")
        sys.exit(1)
    csv_path = sys.argv[1]
    asyncio.run(import_knowledge_database(csv_path, competence_code="resilience"))
