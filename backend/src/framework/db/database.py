# pragma: exclude file
import datetime
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

import anyio
import psycopg
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from pgvector.psycopg import register_vector_async

from framework.api_types.localized_string import LocalizedString

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.api_types.module import Module, Skill, SkillLevel
from framework.api_types.request_format import LearnerModel
from framework.api_types.response_format import Source
from framework.db.db_types import (
    BookDB,
    ChunkDB,
    CompetenceConceptDB,
    CompetenceDB,
    CompetenceLevelDB,
    CompetenceLevelTranslationDB,
    CompetenceTranslationAllLanguagesDB,
    CompetenceTranslationDB,
    ConceptDB,
    ConceptTranslationDB,
    ConceptTranslationJoinedDB,
    ConceptTranslationMultiLanguage,
    JoinedChunk,
    LanguageDB,
    LearningStepDB,
    LearningStepTranslationDB,
    LearningUnitCombined,
    LearningUnitDB,
    LearningUnitForLearnerModel,
    LearningUnitTranslationDB,
    LightCompetenceTranslation,
    PurposeCompleteDB,
    PurposeDB,
    SubDocumentDB,
    TopicDB,
    TopicTranslationDB,
)

load_dotenv()
CONNECTION_STRING = os.getenv("DATABASE_URL")
SCHEMA_FILE = Path(__file__).parent / "sql/metis_schema.sql"
DATA_FILE = Path(__file__).parent / "sql/metis_data.sql"

logger = logging.getLogger(__name__)


class Database:
    """A class to handle database operations using asyncpg."""

    def __init__(self):
        """Initialize the database connection."""
        self.connection = None
        self.book_lang_comp_chunks = set()
        self.book_lang_comp_subdocs = set()

    # general database methods
    async def _ensure_connection(self):
        """Ensure the database connection is active and healthy."""
        if self.connection is None:
            await self.connect()
            return

        # Check if connection is closed or broken
        try:
            if self.connection.closed or self.connection.broken:
                logger.warning(
                    "Database connection is closed or broken. Reconnecting..."
                )
                self.connection = None
                await self.connect()
        except Exception as e:
            logger.warning(f"Error checking connection health: {e}. Reconnecting...")
            self.connection = None
            await self.connect()

    async def connect(self):
        """Connect to the database."""
        if self.connection is None:
            try:
                self.connection = await psycopg.AsyncConnection.connect(
                    CONNECTION_STRING
                )
            except psycopg.OperationalError as e:
                match = re.search(r"/([^/]+)$", CONNECTION_STRING)
                if match:
                    # Retry without database name
                    conn_str_no_db = re.sub(r"/([^/]+)$", "", CONNECTION_STRING)
                    db_name = match.group(1).replace("/", "")
                    logger.error(
                        f"Database '{db_name}' not found. Attempting to create it."
                    )
                    try:
                        # Connect without a specific DB, in autocommit mode to create the new DB
                        async with await psycopg.AsyncConnection.connect(
                            conn_str_no_db, autocommit=True
                        ) as temp_conn:
                            async with temp_conn.cursor() as cursor:
                                await cursor.execute(f"CREATE DATABASE {db_name}")
                                logger.info(
                                    f"Database '{db_name}' created successfully."
                                )

                        # connect to the newly created database
                        self.connection = await psycopg.AsyncConnection.connect(
                            CONNECTION_STRING
                        )
                    except Exception as e:
                        logger.error(
                            f"Error connecting to database even without name: {e}"
                        )
                        raise
                else:
                    # If the pattern doesn't match, the original error is still relevant.
                    logger.error(f"Error connecting to database: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    async def close(self):
        """Close the database connection."""
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    async def execute(self, query: str, params=None):
        """Execute a query on the database."""
        await self._ensure_connection()
        async with self.connection.cursor() as cursor:
            try:
                await cursor.execute(query, params)
                if query.strip().lower().startswith("select"):
                    return await cursor.fetchall()
                else:
                    await self.commit()
                    return None
            except Exception as e:
                await self.rollback()
                logger.error(
                    f"Error executing query: {query}, params: {params}, error: {e}"
                )
                raise

    async def fetchone(self, query: str, params=None):
        """Fetch a single row from the database."""
        await self._ensure_connection()
        async with self.connection.cursor() as cursor:
            try:
                await cursor.execute(query, params)
                return await cursor.fetchone()
            except Exception as e:
                await self.rollback()
                logger.error(
                    f"Error executing query: {query}, params: {params}, error: {e}"
                )
                raise

    async def fetchall(self, query: str, params=None):
        """Fetch all rows from the database."""
        await self._ensure_connection()
        async with self.connection.cursor() as cursor:
            try:
                await cursor.execute(query, params)
                return await cursor.fetchall()
            except Exception as e:
                await self.rollback()
                logger.error(
                    f"Error executing query: {query}, params: {params}, error: {e}"
                )
                raise

    async def commit(self):
        """Commit the current transaction."""
        await self._ensure_connection()
        try:
            await self.connection.commit()
        except (psycopg.OperationalError, psycopg.InterfaceError) as e:
            logger.error(f"Error committing transaction: {e}. Connection may be lost.")
            self.connection = None
            raise

    async def rollback(self):
        """Rollback the current transaction."""
        if self.connection is None or self.connection.closed:
            logger.warning("Cannot rollback: connection is None or closed")
            return
        try:
            await self.connection.rollback()
        except (psycopg.OperationalError, psycopg.InterfaceError) as e:
            logger.error(
                f"Error rolling back transaction: {e}. Connection may be lost."
            )
            self.connection = None

    async def register_vector(self):
        """Register the vector type for use in the database."""
        await self._ensure_connection()
        await register_vector_async(self.connection)

    async def create_database(self, database_name: str = "metis"):
        """Create the database, if it's missing."""
        query = f"CREATE DATABASE {database_name}"
        await self.execute(query)

    async def drop_schema(self, schema_name: str = "public"):
        """Drop a schema from the database."""
        query = f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"
        await self.execute(query)

    async def create_schema(self, schema_name: str = "public"):
        """Create a schema in the database."""
        query = f"CREATE SCHEMA IF NOT EXISTS {schema_name}"
        await self.execute(query)

    async def load_schema(self, schema_file: str = SCHEMA_FILE):
        """Load a schema from a file into the database."""
        await self._ensure_connection()
        with Path.open(schema_file, "r") as file:
            schema_sql = file.read()
        async with self.connection.cursor() as cursor:
            await cursor.execute(schema_sql)
            await self.connection.commit()

    async def load_data(self, data_file: str = DATA_FILE):
        """Load initial data from a file into the database."""
        await self._ensure_connection()

        async with self.connection.cursor() as cursor:
            async with await anyio.open_file(data_file, "r", encoding="utf-8") as f:
                full_sql = await f.read()

                # Remove all block comments (/* ... */)
                full_sql = re.sub(r"/\*.*?\*/", "", full_sql, flags=re.DOTALL)
                # Remove all line comments (-- ...), including the line itself
                full_sql = re.sub(r"^\s*--.*$", "", full_sql, flags=re.MULTILINE)

                # Split into commands, but handle COPY separately
                # The pattern looks for the end of COPY data: \.\n
                parts = re.split(r"\n\\\.\n", full_sql)

                for part in parts:
                    part = part.strip()
                    if not part:
                        continue

                    copy_match = re.search(
                        r"COPY (.*) FROM stdin;", part, re.IGNORECASE | re.DOTALL
                    )

                    if copy_match:
                        # First, execute all SQL commands that appear *before* the COPY statement.
                        pre_copy_sql = part[: copy_match.start()]
                        sql_commands = [
                            cmd.strip()
                            for cmd in pre_copy_sql.split(";")
                            if cmd.strip()
                        ]
                        for command in sql_commands:
                            if command:
                                try:
                                    await cursor.execute(command)
                                except Exception as e:
                                    print(f"Error executing command: {command}\n{e}")
                                    await self.connection.rollback()
                                    return

                        # Now, handle the COPY statement itself.
                        copy_statement = copy_match.group(0)
                        data = part[copy_match.end() :].strip()

                        if data:
                            data_bytes = (data + "\n").encode("utf-8")
                            try:
                                async with cursor.copy(copy_statement) as copy:
                                    await copy.write(data_bytes)
                            except Exception as e:
                                print(f"Error during COPY: {e}")
                                await self.connection.rollback()
                                return
                    else:
                        # This part has no COPY command, just standard SQL.
                        sql_commands = [
                            cmd.strip() for cmd in part.split(";") if cmd.strip()
                        ]
                        for command in sql_commands:
                            if command:
                                try:
                                    await cursor.execute(command)
                                except Exception as e:
                                    print(f"Error executing command: {command}\n{e}")
                                    await self.connection.rollback()
                                    return

            await self.connection.commit()

    async def schema_exists(self) -> bool:
        """Check if the schema exists."""
        await self._ensure_connection()
        query = "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'public'"
        result = await self.fetchone(query)
        return result is not None

    async def get_db_info(self) -> dict:
        """Get basic information about the database."""
        await self._ensure_connection()
        query = "SELECT current_database(), current_user, version()"
        result = await self.fetchone(query)
        return {
            "database": result[0],
            "user": result[1],
            "version": result[2],
        }

    async def get_book(self, book_id: int) -> BookDB:
        """Get a book by its ID."""
        query = "SELECT * FROM book WHERE id = %s AND enabled = TRUE"
        result = await self.fetchone(query, (book_id,))
        return (
            BookDB(
                idbook=result[0],
                title=result[1],
                idlanguage=result[2],
                createdat=result[3],
                updatedat=result[4],
                enabled=result[5],
                authors=result[6],
                code=result[7],
                year=result[8],
            )
            if result
            else None
        )

    async def get_book_by_code(self, book_code: str) -> BookDB:
        """Get a book by its code."""
        query = "SELECT * FROM book WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (book_code,))
        return (
            BookDB(
                idbook=result[0],
                title=result[1],
                idlanguage=result[2],
                createdat=result[3],
                updatedat=result[4],
                enabled=result[5],
                authors=result[6],
                code=result[7],
                year=result[8],
            )
            if result
            else None
        )

    async def get_book_join_language(self, book_id: int) -> tuple[BookDB, LanguageDB]:
        """Get a book and its language by book ID."""
        query = """
            SELECT b.*, l.* 
            FROM book b
            JOIN language l ON b.idlanguage = l.idlanguage
            WHERE b.idbook = %s AND b.enabled = TRUE AND l.enabled = TRUE
        """
        result = await self.fetchone(query, (book_id,))
        if result:
            book_data = result[:9]  # BookDB fields
            language_data = result[9:]  # LanguageDB fields
            return BookDB(
                idbook=book_data[0],
                title=book_data[1],
                idlanguage=book_data[2],
                createdat=book_data[3],
                updatedat=book_data[4],
                enabled=book_data[5],
                authors=book_data[6],
                code=book_data[7],
                year=book_data[8],
            ), LanguageDB(
                idlanguage=language_data[0],
                name=language_data[1],
                createdat=language_data[2],
                updatedat=language_data[3],
                enabled=language_data[4],
                code=language_data[5],
            )
        return None, None

    async def get_books(self) -> list[BookDB]:
        """Get all books from the database."""
        query = "SELECT * FROM book WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                BookDB(
                    idbook=result[0],
                    title=result[1],
                    idlanguage=result[2],
                    createdat=result[3],
                    updatedat=result[4],
                    enabled=result[5],
                    authors=result[6],
                    code=result[7],
                    year=result[8],
                )
                for result in results
            ]
            if results
            else []
        )

    async def add_book(self, book: BookDB) -> int:
        """Add a new book to the database."""
        query = """
            INSERT INTO book (code, title, year, authors, idlanguage, createdat, updatedat, enabled)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
            RETURNING idbook
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    book.code,
                    book.title,
                    book.year,
                    book.authors,
                    book.idlanguage,
                    book.enabled,
                ),
            )
            book_id = await cursor.fetchone()
            await self.connection.commit()
            return book_id[0] if book_id else None

    async def get_language(self, language_code: str) -> LanguageDB:
        """Get a language by its code."""
        query = "SELECT * FROM language WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (language_code,))
        return (
            LanguageDB(
                idlanguage=result[0],
                name=result[1],
                createdat=result[2],
                updatedat=result[3],
                enabled=result[4],
                code=result[5],
            )
            if result
            else None
        )

    async def get_languages(self) -> list[LanguageDB]:
        """Get all languages from the database."""
        query = "SELECT * FROM language WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                LanguageDB(
                    idlanguage=row[0],
                    name=row[1],
                    createdat=row[2],
                    updatedat=row[3],
                    enabled=row[4],
                    code=row[5],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_languages_by_locale(self) -> dict[LocaleType, LanguageDB]:
        """Get languages by locale."""
        languages = await self.get_languages()
        return {lang.code: lang for lang in languages} if languages else {}

    async def add_language(self, language: LanguageDB) -> int:
        """Add a new language to the database."""
        query = """
            INSERT INTO languages (name, code, createdat, updatedat, enabled)
            VALUES (%s, %s, NOW(), NOW(), %s)
            RETURNING idlanguage
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query, (language.name, language.code, language.enabled)
            )
            language_id = await cursor.fetchone()
            await self.connection.commit()
            return language_id[0] if language_id else None

    async def get_competence(self, competence_id: int) -> CompetenceDB:
        """Get a competence by its ID."""
        query = "SELECT * FROM competence WHERE idcompetence = %s AND enabled = TRUE"
        result = await self.fetchone(query, (competence_id,))
        return (
            CompetenceDB(
                idcompetence=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
                idtopic=result[5],
            )
            if result
            else None
        )

    async def get_competence_by_code(self, competence_code: str) -> CompetenceDB:
        """Get a competence by its code."""
        query = "SELECT * FROM competence WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (competence_code,))
        return (
            CompetenceDB(
                idcompetence=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
                idtopic=result[5],
            )
            if result
            else None
        )

    async def get_competence_for_concept(self, concept_id: int) -> CompetenceDB:
        """Get a competence by its ID."""
        query = "SELECT c.* FROM competenceconcept cc LEFT JOIN competence c ON cc.idcompetence = c.idcompetence WHERE cc.idconcept = %s AND c.enabled = TRUE AND cc.enabled = TRUE"
        result = await self.fetchone(query, (concept_id,))
        return (
            CompetenceDB(
                idcompetence=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
                idtopic=result[5],
            )
            if result
            else None
        )

    async def get_competence_translated(
        self, competence_id: int, locale: LocaleType
    ) -> CompetenceTranslationDB:
        """Get a competence by its ID and its associated translation for a locale."""
        query = """
            SELECT ct.*
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            WHERE c.idcompetence = %s AND ct.idlanguage = %s AND c.enabled = TRUE
        """
        result = await self.fetchone(query, (competence_id, locale.value))
        return (
            CompetenceTranslationDB(
                idcompetence=result[0],
                idlanguage=result[1],
                name=result[2],
                description=result[3],
            )
            if result
            else None
        )

    async def get_competence_translated_by_code(
        self, competence_code: str, locale: LocaleType
    ) -> CompetenceTranslationDB:
        """Get a competence by its code and its associated translation for a locale."""
        query = """
            SELECT ct.*
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.code = %s AND l.code = %s AND c.enabled = TRUE
        """
        result = await self.fetchone(query, (competence_code, locale.value))
        return (
            CompetenceTranslationDB(
                idcompetence=result[0],
                idlanguage=result[1],
                name=result[2],
                description=result[3],
            )
            if result
            else None
        )

    async def get_competences(self) -> list[CompetenceDB]:
        """Get all competences from the database."""
        query = "SELECT * FROM competence WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                CompetenceDB(
                    idcompetence=row[0],
                    createdat=row[1],
                    updatedat=row[2],
                    enabled=row[3],
                    code=row[4],
                    idtopic=row[5],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_competences_translated(
        self, locale: LocaleType
    ) -> list[CompetenceTranslationDB]:
        """Get all competences with their translations for a specific locale."""
        query = """
            SELECT ct.*
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE l.code = %s AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (locale.value,))
        return (
            [
                CompetenceTranslationDB(
                    idcompetence=row[0],
                    idlanguage=row[1],
                    name=row[2],
                    description=row[3],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_competence_translations_all_languages(
        self, topic_id: int = 1
    ) -> list[CompetenceTranslationAllLanguagesDB]:
        """Get all competences with their translations for a specific locale."""
        query = """
            SELECT ct.idcompetence, l.code, ct.name, ct.description, c.code
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.idtopic = %s AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (topic_id,))
        ret = {}
        for row in results:
            if row[0] in ret:
                ret[row[0]].name[row[1]] = row[2]
                ret[row[0]].description[row[1]] = row[3]
            else:
                ret[row[0]] = CompetenceTranslationAllLanguagesDB(
                    idcompetence=row[0],
                    code=row[4],
                    name={row[1]: row[2]},
                    description={row[1]: row[3]},
                )
        return list(ret.values())

    async def get_competence_translated_light(
        self, competence_code: str, locale: LocaleType
    ) -> LightCompetenceTranslation:
        """Get a light competence translation by its ID and locale."""
        query = """
            SELECT c.idcompetence, c.code, ct.name, ct.description, l.code
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.code = %s AND l.code = %s AND c.enabled = TRUE
        """
        result = await self.fetchone(query, (competence_code, locale.value))
        return (
            LightCompetenceTranslation(
                idcompetence=result[0],
                code=result[1],
                name=result[2],
                description=result[3],
                language_code=result[4],
            )
            if result
            else None
        )

    async def get_competences_translated_light(
        self, locale: LocaleType
    ) -> list[LightCompetenceTranslation]:
        """Get all competences with their translations for a specific locale in a light format."""
        query = """
            SELECT c.idcompetence, c.code, ct.name, ct.description, l.code
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE l.code = %s AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (locale.value,))
        return (
            [
                LightCompetenceTranslation(
                    idcompetence=row[0],
                    code=row[1],
                    name=row[2],
                    description=row[3],
                    language_code=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def add_competence(self, competence: CompetenceDB) -> int:
        """Add a new competence to the database."""
        query = """
            INSERT INTO competence (code, createdat, updatedat, enabled, idtopic)
            VALUES (%s, NOW(), NOW(), %s, %s)
            RETURNING idcompetence
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query, (competence.code, competence.enabled, competence.idtopic)
            )
            competence_id = await cursor.fetchone()
            await self.connection.commit()
            return competence_id[0] if competence_id else None

    async def add_competence_concept(self, competenceconcept: CompetenceConceptDB):
        """Add a new competence-concept relationship to the database."""
        query = """
            INSERT INTO competenceconcept (idcompetence, idconcept, createdat, enabled)
            VALUES (%s, %s, NOW(), TRUE)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query, (competenceconcept.idcompetence, competenceconcept.idconcept)
            )
            await self.connection.commit()

    async def get_topic(self, topic_id: int) -> TopicDB:
        """Get a topic by its ID."""
        query = "SELECT * FROM topic WHERE idtopic = %s AND enabled = TRUE"
        result = await self.fetchone(query, (topic_id,))
        return (
            TopicDB(
                idtopic=result[0],
                code=result[1],
                createdat=result[2],
                updatedat=result[3],
                enabled=result[4],
            )
            if result
            else None
        )

    async def get_topics(self) -> list[TopicDB]:
        """Get all topics from the database."""
        query = "SELECT * FROM topic WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                TopicDB(
                    idtopic=row[0],
                    code=row[1],
                    createdat=row[2],
                    updatedat=row[3],
                    enabled=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_topic_by_code(self, topic_code: str) -> TopicDB:
        """Get a topic by its code."""
        query = "SELECT * FROM topic WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (topic_code,))
        return (
            TopicDB(
                idtopic=result[0],
                code=result[1],
                createdat=result[2],
                updatedat=result[3],
                enabled=result[4],
            )
            if result
            else None
        )

    async def add_topic(self, topic: TopicDB) -> int:
        """Add a new topic to the database."""
        query = """
            INSERT INTO topic (code, createdat, updatedat, enabled)
            VALUES (%s, NOW(), NOW(), %s)
            RETURNING idtopic
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, (topic.code, topic.enabled))
            topic_id = await cursor.fetchone()
            await self.connection.commit()
            return topic_id[0] if topic_id else None

    async def add_topic_translation(self, topic_translation: TopicTranslationDB) -> int:
        """Add a new topic translation to the database."""
        query = """
            INSERT INTO topictranslation (idtopic, idlanguage, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    topic_translation.idtopic,
                    topic_translation.idlanguage,
                    topic_translation.name,
                    topic_translation.description,
                ),
            )
            translation_id = await cursor.fetchone()
            await self.connection.commit()
            return translation_id[0] if translation_id else None

    async def get_skill_by_code(self, skill_code: str) -> Skill:
        """Get a skill by its code."""
        query = """
            SELECT s.idcompetence, s.code, st.name, st.description, l.code
            FROM competence s
            JOIN competencetranslation st ON s.idcompetence = st.idcompetence
            JOIN language l ON st.idlanguage = l.idlanguage
            WHERE s.code = %s AND s.enabled = TRUE
        """
        result = await self.fetchone(query, (skill_code,))
        if result:
            return Skill(
                id=result[0],
                code=result[1],
                title={LocaleType(result[4]): result[2]},
                description={LocaleType(result[4]): result[3]},
                levels=[],  # TODO
            )
        return None

    async def get_skills(self, topic_id: int) -> list[Skill]:
        """Get all skills from the database."""
        # fetch all competences with their translations
        query = """
            SELECT c.idcompetence, c.code, ct.name, ct.description, l.code
            FROM competence c
            LEFT JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.idtopic = %s AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (topic_id,))
        skills = {}
        for row in results:
            if row[0] not in skills:
                idcompetence = row[0]
                # Fetch all competence levels
                query = """
                    SELECT cl.idcompetencelevel, cl.code, clt.name, clt.description, l.code
                    FROM competencelevel cl
                    LEFT JOIN competenceleveltranslation clt ON cl.idcompetencelevel = clt.idcompetencelevel
                    LEFT JOIN language l ON clt.idlanguage = l.idlanguage
                    WHERE cl.enabled = TRUE
                """
                results_levels = await self.fetchall(query)
                levels = {}
                for levels_row in results_levels:
                    if levels_row[0] not in levels:
                        # fetch all concepts that are associated with a learning unit that is associated with this competence level and competence
                        query = """
                            SELECT l.code, ct.*
                            FROM learningunit lu
                            LEFT JOIN concepttranslation ct ON lu.idconcept = ct.idconcept
                            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
                            WHERE lu.idcompetencelevel = %s
                            AND lu.idconcept IN (
                                SELECT idconcept 
                                FROM competenceconcept
                                WHERE idcompetence = %s
                            )
                            AND lu.enabled = TRUE
                            GROUP BY l.code, ct.idconcept, ct.idlanguage
                        """
                        learning_goals = {}
                        concepts_per_lang = {}
                        concepts = await self.fetchall(
                            query, (levels_row[0], idcompetence)
                        )
                        for concept_row in concepts:
                            if LocaleType(concept_row[0]) not in concepts_per_lang:
                                concepts_per_lang[LocaleType(concept_row[0])] = []
                            concepts_per_lang[LocaleType(concept_row[0])].append(
                                ConceptTranslationDB(
                                    idconcept=concept_row[1],
                                    idlanguage=concept_row[2],
                                    name=concept_row[3],
                                    description=concept_row[4],
                                )
                            )
                        for lang, concept_list in concepts_per_lang.items():
                            learning_goals[lang] = ", ".join(
                                [concept.name for concept in concept_list]
                            )
                        levels[levels_row[0]] = SkillLevel(
                            id=levels_row[0],
                            code=levels_row[1],
                            title={LocaleType(levels_row[4]): levels_row[2]},
                            description={LocaleType(levels_row[4]): levels_row[3]},
                            learning_goals=learning_goals,
                        )
                    else:
                        levels[levels_row[0]].title[LocaleType(levels_row[4])] = (
                            levels_row[2]
                        )
                        levels[levels_row[0]].description[LocaleType(levels_row[4])] = (
                            levels_row[3]
                        )
                skills[row[0]] = Skill(
                    id=row[0],
                    code=row[1],
                    title={LocaleType(row[4]): row[2]},
                    description={LocaleType(row[4]): row[3]},
                    levels=list(levels.values()),
                )
            else:
                skills[row[0]].title[LocaleType(row[4])] = row[2]
                skills[row[0]].description[LocaleType(row[4])] = row[3]

        return list(skills.values())

    async def get_modules(self, topic_id: int) -> list[Module]:
        """Get all modules (competences) for a specific topic."""
        query = """
            SELECT c.idcompetence, c.code, ct.name, ct.description, l.code
            FROM competence c
            JOIN competencetranslation ct ON c.idcompetence = ct.idcompetence
            JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.idtopic = %s AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (topic_id,))
        modules = {}
        for row in results:
            if row[0] not in modules:
                modules[row[0]] = Module(
                    id=row[0],
                    code=row[1],
                    title={LocaleType(row[4]): row[2]},
                )
            else:
                modules[row[0]].title[LocaleType(row[4])] = row[2]

        return list(modules.values())

    async def get_learning_step(self, learning_step_id: int) -> LearningStepDB:
        """Get a learning step by its ID."""
        query = """
            SELECT *
            FROM learningstep
            WHERE idstep = %s AND enabled = TRUE
        """
        result = await self.fetchone(query, (learning_step_id,))
        return (
            LearningStepDB(
                idstep=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
            )
            if result
            else None
        )

    async def get_learning_step_by_name(
        self, learning_step_name: str
    ) -> LearningStepDB:
        """Get a learning step by its name."""
        query = """
            SELECT *
            FROM learningstep
            JOIN learningsteptranslation ON learningstep.idstep = learningsteptranslation.idstep
            WHERE name = %s AND enabled = TRUE
        """
        result = await self.fetchone(query, (learning_step_name,))
        return (
            LearningStepDB(
                idstep=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
            )
            if result
            else None
        )

    async def add_learning_step(self, learning_step: LearningStepDB) -> int:
        """Add a new learning step to the database."""
        query = """
            INSERT INTO learningstep (code, createdat, updatedat, enabled)
            VALUES (%s, NOW(), NOW(), %s)
            RETURNING idstep
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, (learning_step.code, learning_step.enabled))
            learning_step_id = await cursor.fetchone()
            await self.connection.commit()
            return learning_step_id[0] if learning_step_id else None

    async def add_learning_step_translation(
        self, learning_step_translation: LearningStepTranslationDB
    ) -> int:
        """Add a new learning step translation to the database."""
        query = """
            INSERT INTO learningsteptranslation (idstep, idlanguage, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING idsteptranslation
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    learning_step_translation.idstep,
                    learning_step_translation.idlanguage,
                    learning_step_translation.name,
                    learning_step_translation.description,
                ),
            )
            learning_step_translation_id = await cursor.fetchone()
            await self.connection.commit()
            return (
                learning_step_translation_id[0]
                if learning_step_translation_id
                else None
            )

    async def get_competence_level(self, competence_level_id: int) -> CompetenceLevelDB:
        """Get a competence level by its ID."""
        query = "SELECT * FROM competencelevel WHERE idcompetencelevel = %s AND enabled = TRUE"
        result = await self.fetchone(query, (competence_level_id,))
        return (
            CompetenceLevelDB(
                idcompetencelevel=result[0],
                code=result[1],
                createdat=result[2],
                updatedat=result[3],
                enabled=result[4],
            )
            if result
            else None
        )

    async def get_competence_levels(self) -> list[CompetenceLevelDB]:
        """Get all competence levels from the database."""
        query = "SELECT * FROM competencelevel WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                CompetenceLevelDB(
                    idcompetencelevel=row[0],
                    createdat=row[1],
                    updatedat=row[2],
                    enabled=row[3],
                    code=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_competence_level_translated(
        self, competence_level_id: int, locale: LocaleType
    ) -> CompetenceLevelTranslationDB:
        """Get a competence level by its ID and its associated translation."""
        query = """
            SELECT clt.*
            FROM competenceleveltranslation clt
            LEFT JOIN language l ON clt.idlanguage = l.idlanguage
            WHERE clt.idcompetencelevel = %s AND l.code = %s
        """
        result = await self.fetchone(query, (competence_level_id, locale.value))
        return (
            CompetenceLevelTranslationDB(
                idcompetencelevel=result[0],
                idlanguage=result[1],
                name=result[2],
                description=result[3],
            )
            if result
            else None
        )

    async def add_competence_level(self, competence_level: CompetenceLevelDB) -> int:
        """Add a new competence level to the database."""
        query = """
            INSERT INTO competencelevel (code, createdat, updatedat, enabled)
            VALUES (%s, NOW(), NOW(), %s)
            RETURNING idcompetencelevel
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query, (competence_level.code, competence_level.enabled)
            )
            competence_level_id = await cursor.fetchone()
            await self.connection.commit()
            return competence_level_id[0] if competence_level_id else None

    async def add_competence_level_translation(
        self, competence_level_translation: CompetenceLevelTranslationDB
    ) -> int:
        """Add a new competence level translation to the database."""
        query = """
            INSERT INTO competenceleveltranslation (idcompetencelevel, idlanguage, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING idcompetenceleveltranslation
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    competence_level_translation.idcompetencelevel,
                    competence_level_translation.idlanguage,
                    competence_level_translation.name,
                    competence_level_translation.description,
                ),
            )
            competence_level_translation_id = await cursor.fetchone()
            await self.connection.commit()
            return (
                competence_level_translation_id[0]
                if competence_level_translation_id
                else None
            )

    async def get_concept(self, concept_id: int) -> ConceptDB:
        """Get a concept by its ID."""
        query = "SELECT * FROM concept WHERE idconcept = %s AND enabled = TRUE"
        result = await self.fetchone(query, (concept_id,))
        return (
            ConceptDB(
                idconcept=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
            )
            if result
            else None
        )

    async def get_concept_by_code(self, concept_code: str) -> ConceptDB:
        """Get a concept by its code."""
        query = "SELECT * FROM concept WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (concept_code,))
        return (
            ConceptDB(
                idconcept=result[0],
                createdat=result[1],
                updatedat=result[2],
                enabled=result[3],
                code=result[4],
            )
            if result
            else None
        )

    async def get_concept_translation(
        self, concept_id: int, language_id: int
    ) -> ConceptTranslationDB:
        """Get a concept translation by its ID and language ID."""
        query = """
            SELECT *
            FROM concepttranslation
            WHERE idconcept = %s AND idlanguage = %s AND enabled = TRUE
        """
        result = await self.fetchone(query, (concept_id, language_id))
        return (
            ConceptTranslationDB(
                idconcept=result[0],
                idlanguage=result[1],
                name=result[2],
                description=result[3],
            )
            if result
            else None
        )

    async def get_concept_translated_by_code(
        self, concept_code: str, locale: LocaleType
    ) -> ConceptTranslationDB:
        """Get a concept by its code and its associated translation for a locale."""
        query = """
            SELECT ct.*
            FROM concept c
            LEFT JOIN concepttranslation ct ON c.idconcept = ct.idconcept
            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE c.code = %s AND l.code = %s AND c.enabled = TRUE AND ct.enabled = TRUE
        """
        result = await self.fetchone(query, (concept_code, locale.value))
        return (
            ConceptTranslationDB(
                idconcept=result[0],
                idlanguage=result[1],
                name=result[2],
                description=result[3],
            )
            if result
            else None
        )

    async def add_concept(self, concept: ConceptDB) -> int:
        """Add a new concept to the database."""
        query = """
            INSERT INTO concept (code, createdat, updatedat, enabled)
            VALUES (%s, NOW(), NOW(), %s)
            RETURNING idconcept
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, (concept.code, concept.enabled))
            concept_id = await cursor.fetchone()
            await self.connection.commit()
            return concept_id[0] if concept_id else None

    async def add_concept_translation(
        self, concept_translation: ConceptTranslationDB
    ) -> bool:
        """Add a new concept translation to the database."""
        query = """
            INSERT INTO concepttranslation (idconcept, idlanguage, name, description)
            VALUES (%s, %s, %s, %s)
        """
        try:
            await self.execute(
                query,
                (
                    concept_translation.idconcept,
                    concept_translation.idlanguage,
                    concept_translation.name,
                    concept_translation.description,
                ),
            )
            return True
        except psycopg.errors.UniqueViolation as e:
            logger.info(f"Concept '{concept_translation.name}' already exists.")
            logger.debug(f"Error details: {e}")
            await self.rollback()
            return False

    async def get_competence_concept(
        self, competence_id: int, concept_id: int
    ) -> Optional[int]:
        """Get a competence-concept relationship by competence and concept IDs."""
        query = """
            SELECT idcompetenceconcept
            FROM competenceconcept
            WHERE idcompetence = %s AND idconcept = %s AND enabled = TRUE
        """
        result = await self.fetchone(query, (competence_id, concept_id))
        return result[0] if result else None

    async def get_learning_unit(self, idlearningunit: int) -> LearningUnitDB:
        """Get a learning unit by its ID."""
        query = (
            "SELECT * FROM learningunit WHERE idlearningunit = %s AND enabled = TRUE"
        )
        result = await self.fetchone(query, (idlearningunit,))
        return (
            LearningUnitDB(
                idlearningunit=result[0],
                idstep=result[1],
                idcompetencelevel=result[2],
                idconcept=result[3],
                createdat=result[4],
                updatedat=result[5],
                enabled=result[6],
            )
            if result
            else None
        )

    async def get_concepts_not_completed_yet(
        self,
        competence_id: int,
        competence_level_id: int,
        completed_luids: list[int],
        language_code: str,
    ) -> list[ConceptTranslationDB]:
        """Get concepts that have not been completed yet for a specific competence and competence level."""
        # retrieve only concepts that have not yet been completed
        # a concept is considered completed if all associated learning units for the given competence level are completed
        query = """
            SELECT ct.*
            FROM learningunit lu
            LEFT JOIN concept c ON lu.idconcept = c.idconcept
            LEFT JOIN concepttranslation ct ON ct.idconcept = lu.idconcept
            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE lu.idlearningunit NOT IN %s AND l.code = %s AND lu.idcompetencelevel = %s AND lu.idconcept IN (SELECT idconcept FROM competenceconcept WHERE idcompetence = %s) AND lu.enabled = TRUE AND c.enabled = TRUE AND ct.enabled = TRUE
            GROUP BY ct.idlanguage, ct.idconcept ORDER BY idconcept ASC
        """
        results = await self.fetchall(
            query,
            (
                tuple(completed_luids),
                language_code,
                competence_level_id,
                competence_id,
            ),
        )
        return (
            [
                ConceptTranslationDB(
                    idconcept=row[0],
                    idlanguage=row[1],
                    name=row[2],
                    description=row[3],
                )
                for row in results
            ]
            if results
            else []
        )

    async def add_learning_unit(self, learning_unit: LearningUnitDB) -> int:
        """Add a new learning unit to the database."""
        query = """
            INSERT INTO learningunit (idstep, idcompetencelevel, idconcept, createdat, updatedat, enabled)
            VALUES (%s, %s, %s, NOW(), NOW(), TRUE)
            RETURNING idlearningunit
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    learning_unit.idstep,
                    learning_unit.idcompetencelevel,
                    learning_unit.idconcept,
                ),
            )
            learning_unit_id = await cursor.fetchone()
            await self.connection.commit()
            return learning_unit_id[0] if learning_unit_id else None

    async def add_learning_unit_translation(
        self, learning_unit_translation: LearningUnitTranslationDB
    ) -> None:
        """Add a new learning unit translation to the database."""
        query = """
            INSERT INTO learningunittranslation (idlearningunit, idlanguage, learninggoal, task, solution)
            VALUES (%s, %s, %s, %s, %s)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    learning_unit_translation.idlearningunit,
                    learning_unit_translation.idlanguage,
                    learning_unit_translation.learninggoal,
                    learning_unit_translation.task,
                    learning_unit_translation.solution,
                ),
            )
            await self.connection.commit()

    async def get_learning_units_for_level(
        self,
        concept_id: int,
        locale: LocaleType,
        competence_level_id: Optional[int] = None,
        excluded_luids: list[int] = None,
        only_luids: list[int] = None,
    ) -> list[LearningUnitCombined]:
        """Get learning units for a specific concept and competence level."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.idconcept = %s AND l.code = %s AND lu.enabled = TRUE
        """
        fetch_params = (concept_id, locale.value)
        if competence_level_id is not None:
            query += " AND lu.idcompetencelevel = %s"
            fetch_params += (competence_level_id,)
        if excluded_luids:
            query += " AND lu.idlearningunit != ALL(%s)"
            fetch_params += (excluded_luids,)
        elif only_luids:
            query += " AND lu.idlearningunit = ANY(%s)"
            fetch_params += (only_luids,)
        results = await self.fetchall(query, fetch_params)
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_learning_units_by_level_for_learner_model(
        self, concept_id: int, competence_level_id: int = None
    ) -> list[LearningUnitForLearnerModel]:
        """Get learning units for a specific concept and competence level."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lu.code, lut.name, l.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.idconcept = %s AND lu.enabled = TRUE
        """
        params = (concept_id,)
        if competence_level_id:
            query += " AND lu.idcompetencelevel = %s"
            params = (concept_id, competence_level_id)

        results = await self.fetchall(query, params)
        lus = {}
        for row in results:
            if row[0] in lus:
                lus[row[0]].name[row[6]] = row[5]
            else:
                lus[row[0]] = LearningUnitForLearnerModel(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    code=row[4],
                    name={row[6]: row[5]},
                )

        return lus.values()

    async def get_learning_units_for_competence_and_level(
        self,
        competence_id: int,
        locale: LocaleType,
        competence_level_id: Optional[int] = None,
        excluded_luids: list[int] = None,
        only_luids: list[int] = None,
    ) -> list[LearningUnitCombined]:
        """Get all learning units for a specific competence and competence level."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.idconcept IN (
                SELECT idconcept 
                FROM competenceconcept 
                WHERE idcompetence = %s
            )
            AND l.code = %s AND lu.enabled = TRUE
        """
        fetch_params = (competence_id, locale.value)
        if competence_level_id is not None:
            query += " AND lu.idcompetencelevel = %s"
            fetch_params += (competence_level_id,)
        if excluded_luids:
            query += " AND lu.idlearningunit != ALL(%s)"
            fetch_params += (excluded_luids,)
        elif only_luids:
            query += " AND lu.idlearningunit = ANY(%s)"
            fetch_params += (only_luids,)
        results = await self.fetchall(query, fetch_params)
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_chunk_table_exists(self) -> bool:
        """Check if the chunk table exists in the database."""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chunk'
            )
        """
        result = await self.fetchone(query)
        return result[0] if result else False

    async def get_chunk(self, idchunk: int) -> ChunkDB:
        """Get a chunk by its id."""
        query = "SELECT * FROM chunk WHERE idchunk = %s AND enabled = TRUE"
        result = await self.fetchone(query, (idchunk,))
        return (
            ChunkDB(
                idchunk=result[0],
                content=result[1],
                embedding=result[2],  # Assuming embedding is stored as a list or array
                idbook=result[3],
                idlanguage=result[4],
                createdat=result[5],
                updatedat=result[6],
                enabled=result[7],
            )
            if result
            else None
        )

    def _convert_chunk_joined(self, result) -> JoinedChunk:
        """Convert a result of a query for chunks into a JoinedChunk object."""
        result_columns = [
            "idchunk",
            "content",
            "idbook",
            "idlanguage",
            "createdat",
            "updatedat",
            "enabled",
            "idcompetence",
            "idtopic",
            "embedding",
            "idsubdocument",
            "l_code",
            "authors",
            "year",
            "title",
            "book_l_code",
            "competence_code",
            "sd_content",
        ]
        result_data = {col: result[i] for i, col in enumerate(result_columns)}
        return JoinedChunk(
            chunk=ChunkDB(
                idchunk=result_data["idchunk"],
                content=result_data["content"],
                embedding=[],  # result_data['embedding']
                idbook=result_data["idbook"],
                idlanguage=result_data["idlanguage"],
                idtopic=result_data["idtopic"],
                idcompetence=result_data["idcompetence"],
                idsubdocument=result_data.get("idsubdocument", None),  # Optional field
                createdat=result_data["createdat"],
                updatedat=result_data["updatedat"],
                enabled=result_data["enabled"],
            ),
            chunk_language=LocaleType(result_data["l_code"])
            if result_data["l_code"]
            else LocaleType.EN,
            source=Source(
                title=result_data["title"],
                chunk=result_data.get("sd_content", result_data["content"]),
                thumbnail=None,  # Assuming thumbnail is not available in this query
                year=result_data["year"],
                authors=result_data["authors"] if result_data["authors"] else [],
                original_language=LocaleType(result_data["book_l_code"]),
            ),
            competence_id=result_data["idcompetence"],
            competence_code=result_data["competence_code"],
            subdocument_content=result_data.get("sd_content", None),  # Optional field
        )

    async def get_chunk_joined(self, chunkid) -> JoinedChunk:
        """Get a chunk and its related entities by chunk ID."""
        query = """
            SELECT c.*, l.code, b.authors, b.year, b.title, lb.code, co.code FROM chunk c
            LEFT JOIN language l ON c.idlanguage = l.idlanguage
            LEFT JOIN book b ON c.idbook = b.idbook
            LEFT JOIN language lb ON b.idlanguage = lb.idlanguage
            LEFT JOIN competence co ON c.idcompetence = co.idcompetence
            WHERE c.idchunk = %s AND c.enabled = TRUE
        """
        result = await self.fetchone(query, (chunkid,))
        if result:
            return self._convert_chunk_joined(result)
        return None

    async def get_chunks_joined(self, chunkids: list[int]) -> list[JoinedChunk]:
        """Get multiple chunks and their related entities by chunk IDs."""
        if not chunkids:
            return []

        query = """
            SELECT c.*, l.code, b.authors, b.year, b.title, lb.code, co.code, sd.content FROM chunk c
            LEFT JOIN language l ON c.idlanguage = l.idlanguage
            LEFT JOIN book b ON c.idbook = b.idbook
            LEFT JOIN language lb ON b.idlanguage = lb.idlanguage
            LEFT JOIN competence co ON c.idcompetence = co.idcompetence
            LEFT JOIN subdocument sd ON c.idsubdocument = sd.idsubdocument
            WHERE c.idchunk = ANY(%s) AND c.enabled = TRUE
        """
        results = await self.fetchall(query, (chunkids,))
        joined_chunks = []
        for result in results:
            joined_chunks.append(self._convert_chunk_joined(result))
        return joined_chunks

    async def get_learning_units_joined(
        self, learning_unit_ids: list[int], locale: LocaleType
    ) -> list[LearningUnitCombined]:
        """Get learning units by their IDs and locale."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.idlearningunit = ANY(%s) AND l.code = %s AND lu.enabled = TRUE
        """
        results = await self.fetchall(query, (learning_unit_ids, locale.value))
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_learning_units_joined_without_competences(
        self,
        learning_unit_ids: list[int],
        locale: LocaleType,
        only_competences: list[str],
    ) -> list[LearningUnitCombined]:
        """Get learning units by their IDs and locale."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            LEFT JOIN competenceconcept cc ON lu.idconcept = cc.idconcept
            LEFT JOIN competence c ON cc.idcompetence = c.idcompetence
            WHERE lu.idlearningunit = ANY(%s) AND l.code = %s AND c.code = ANY(%s) 
            AND lu.enabled = TRUE AND c.enabled = TRUE
        """
        results = await self.fetchall(
            query, (learning_unit_ids, locale.value, only_competences)
        )
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_learning_units_joined_by_code(
        self, learning_unit_codes: list[str], locale: LocaleType
    ) -> list[LearningUnitCombined]:
        """Get learning units by their codes and locale."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
            lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.code = ANY(%s) AND l.code = %s AND lu.enabled = TRUE
        """
        results = await self.fetchall(query, (learning_unit_codes, locale.value))
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_following_learning_units_for_learner_model(
        self,
        learner_model: LearnerModel,
        locale: LocaleType,
        only_competences: list[str] = None,
    ) -> list[LearningUnitCombined]:
        """Get learning units that the user will need to learn next based on their learner model.

        This method retrieves learning units that are not in the completed list
        and are associated with the selected competence and current competence level.
        The DB returns the units that are still missing of the current competence level.
        """
        luids = []

        completed_luids = [
            lu.id
            for lu in learner_model.learning_units.values()
            if lu.completed is True
        ]
        for competence in learner_model.competences.values():
            if (
                competence.competence_code not in only_competences
                if only_competences
                else False
            ):
                continue
            for concept in competence.concepts.values():
                concept_id = concept.concept_id
                following_luids = await self.get_following_learning_units(
                    completed_learning_unit_ids=completed_luids,
                    selected_concept_id=concept_id,
                    locale=locale,
                    # for now, remove the competence level and retrieve all LUs
                )
                luids.extend(following_luids)

        return luids

    async def get_following_learning_units(
        self,
        completed_learning_unit_ids: list[int],
        selected_concept_id: int,
        locale: LocaleType,
        cur_competence_level_id: Optional[int] = None,
    ) -> list[LearningUnitCombined]:
        """Get learning units that the user will need to learn next.

        This method retrieves learning units that are not in the completed list
        and are associated with the specified competence and current competence level.
        The DB returns the units that are still missing of the current competence level.
        """
        if not completed_learning_unit_ids:
            # If no completed units, get all units for the level
            query = """
                SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
                lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
                FROM learningunit lu
                INNER JOIN learningunittranslation lut 
                    ON lu.idlearningunit = lut.idlearningunit
                INNER JOIN language l ON lut.idlanguage = l.idlanguage
                INNER JOIN concept c ON lu.idconcept = c.idconcept
                WHERE lu.enabled = TRUE AND c.enabled = TRUE
                AND c.idconcept = %s
                AND l.code = %s
            """
            parameters = (
                selected_concept_id,
                locale.value,
            )
            if cur_competence_level_id is not None:
                query += " AND lu.idcompetencelevel = %s"
                parameters += (cur_competence_level_id,)
            results = await self.fetchall(query, parameters)
        else:
            query = """
                SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept,
                lut.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
                FROM learningunit lu
                INNER JOIN learningunittranslation lut 
                    ON lu.idlearningunit = lut.idlearningunit
                INNER JOIN language l ON lut.idlanguage = l.idlanguage
                INNER JOIN concept c ON lu.idconcept = c.idconcept
                WHERE lu.enabled = TRUE AND c.enabled = TRUE
                AND lu.idlearningunit != ALL(%s)
                AND c.idconcept = %s
                AND l.code = %s
            """
            parameters = (
                completed_learning_unit_ids,
                selected_concept_id,
                locale.value,
            )
            if cur_competence_level_id is not None:
                query += " AND lu.idcompetencelevel = %s"
                parameters += (cur_competence_level_id,)
            results = await self.fetchall(
                query,
                parameters,
            )
        return (
            [
                LearningUnitCombined(
                    idlearningunit=row[0],
                    idstep=row[1],
                    idcompetencelevel=row[2],
                    idconcept=row[3],
                    idlanguage=row[4],
                    language_code=row[5],
                    learning_goal=row[6],
                    task=row[7],
                    solution=row[8],
                    name=row[9],
                    code=row[10],
                )
                for row in results
            ]
            if results
            else []
        )

    async def update_learning_unit_code(
        self, idlearningunit: int, new_code: str
    ) -> bool:
        """Update the code of a learning unit."""
        query = """
            UPDATE learningunit
            SET code = %s, updatedat = NOW()
            WHERE idlearningunit = %s
        """
        try:
            await self.execute(query, (new_code, idlearningunit))
            return True
        except Exception as e:
            logger.error(f"Error updating learning unit code: {e}")
            await self.rollback()
            return False

    async def update_learning_unit_name(
        self, idlearningunit: int, name: LocalizedString
    ) -> bool:
        """Update the name of a learning unit."""
        query = """
            UPDATE learningunittranslation
            SET name = %s
            WHERE idlearningunit = %s AND idlanguage = (SELECT idlanguage FROM language WHERE code = %s)
        """
        try:
            await self.execute(query, (name.de(), idlearningunit, "de"))
            await self.execute(query, (name.en(), idlearningunit, "en"))
        except Exception as e:
            logger.error(f"Error updating learning unit name: {e}")
            await self.rollback()
            return False

    async def add_subdocument(self, subdocument: SubDocumentDB) -> int:
        """Add a subdocument to the database."""
        if (
            subdocument.idbook,
            subdocument.idlanguage,
            subdocument.idcompetence,
        ) not in self.book_lang_comp_subdocs:
            await self.disable_subdocuments(
                subdocument.idbook, subdocument.idlanguage, subdocument.idcompetence
            )
            self.book_lang_comp_subdocs.add(
                (subdocument.idbook, subdocument.idlanguage, subdocument.idcompetence)
            )

        query = """
            INSERT INTO subdocument (content, idbook, idlanguage, idcompetence, enabled, createdat, updatedat, idtopic)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
            RETURNING idsubdocument
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    subdocument.content,
                    subdocument.idbook,
                    subdocument.idlanguage,
                    subdocument.idcompetence,
                    subdocument.enabled,
                    subdocument.idtopic,
                ),
            )
            subdocument_id = await cursor.fetchone()
            await self.connection.commit()
            return subdocument_id[0] if subdocument_id else None

    async def get_subdocument(self, subdocument_id: int) -> SubDocumentDB:
        """Get a subdocument by its ID."""
        query = "SELECT * FROM subdocument WHERE idsubdocument = %s AND enabled = TRUE"
        result = await self.fetchone(query, (subdocument_id,))
        return (
            SubDocumentDB(
                idsubdocument=result[0],
                content=result[1],
                idbook=result[2],
                idlanguage=result[3],
                idcompetence=result[4],
                enabled=result[5],
                createdat=result[6],
                updatedat=result[7],
                idtopic=result[8],
            )
            if result
            else None
        )

    async def disable_chunks(self, idbook: int, idlanguage: int, idcompetence: int):
        """Disable all chunks for a given book, language, and competence."""
        await self.execute(
            """
            UPDATE chunk
            SET enabled = FALSE
            WHERE idbook = %s AND idlanguage = %s AND idcompetence = %s
            """,
            (idbook, idlanguage, idcompetence),
        )

    async def disable_subdocuments(
        self, idbook: int, idlanguage: int, idcompetence: int
    ):
        """Disable all subdocuments for a given book, language, and competence."""
        await self.execute(
            """
            UPDATE subdocument
            SET enabled = FALSE
            WHERE idbook = %s AND idlanguage = %s AND idcompetence = %s
            """,
            (idbook, idlanguage, idcompetence),
        )

    async def add_chunk(self, cur, chunk: ChunkDB, language_code: Optional[str] = None):
        """Add a chunk to the database with an embedding."""
        # If language_code is provided, get the idlanguage
        if language_code:
            chunk.idlanguage = (
                await self.get_language(language_code)
            ).idlanguage or chunk.idlanguage

        async with cur.copy(
            "COPY chunk (content, idbook, idlanguage, createdat, updatedat, enabled, idcompetence, idtopic, embedding, idsubdocument) FROM STDIN WITH (FORMAT BINARY)"
        ) as acopy:
            acopy.set_types(
                [
                    "text",  # content
                    "integer",  # idbook
                    "integer",  # idlanguage
                    "timestamp",  # createdat
                    "timestamp",  # updatedat
                    "boolean",  # enabled
                    "integer",  # idcompetence
                    "integer",  # idtopic
                    "halfvec",  # embedding
                    # "vector",  # embedding
                    "integer",  # idsubdocument
                ]
            )

            # Write the data to the copy
            await acopy.write_row(
                [
                    chunk.content,
                    chunk.idbook,
                    chunk.idlanguage,
                    chunk.createdat,
                    chunk.updatedat,
                    chunk.enabled,
                    chunk.idcompetence,
                    chunk.idtopic,
                    chunk.embedding,
                    chunk.idsubdocument,
                ]
            )

    async def add_documents(
        self,
        embedding_func: Embeddings,
        docs: list[Document],
    ):
        """Embeds the chunks and saves them to the PostgreSQL database."""
        languages = await self.get_languages()
        language_ids = {lang.code: lang.idlanguage for lang in languages}
        book_code_to_id = {}
        competence_code_to_id = {}
        topic_code_to_id = {}
        async with self.connection.cursor() as cur:
            embeddings = await embedding_func.aembed_documents(
                [doc.page_content for doc in docs]
            )
            logger.info(
                f":check_mark: Embeddings generated for {len(embeddings)} documents."
            )
            for i, doc in enumerate(docs):
                language_code = doc.metadata.get("language", "en")

                # book
                try:
                    if "idbook" in doc.metadata:
                        book_id = doc.metadata["idbook"]
                    elif doc.metadata["book_code"] not in book_code_to_id:
                        book_id = (
                            await self.get_book_by_code(doc.metadata["book_code"])
                        ).idbook
                        book_code_to_id[doc.metadata["book_code"]] = book_id
                    else:
                        book_id = book_code_to_id[doc.metadata["book_code"]]
                    if not book_id:
                        raise ValueError("Book ID is None")
                except Exception as e:
                    logger.warning(
                        f"Error retrieving book for code {doc.metadata.get('book_code', None)}: {e}. "
                        "Skipping chunk addition."
                    )
                    continue

                # competence
                if "idcompetence" in doc.metadata:
                    competence_id = doc.metadata["idcompetence"]
                elif doc.metadata.get("competence") not in competence_code_to_id:
                    competence_id = (
                        await self.get_competence_by_code(
                            doc.metadata.get("competence", None)
                        )
                    ).idcompetence
                    competence_code_to_id[doc.metadata.get("competence")] = (
                        competence_id
                    )
                else:
                    competence_id = competence_code_to_id[
                        doc.metadata.get("competence")
                    ]
                if not competence_id:
                    logger.warning(
                        f"Competence ID not found for code {doc.metadata.get('competence', None)}. "
                        "Skipping chunk addition."
                    )
                    continue

                # topic
                if "idtopic" in doc.metadata:
                    topic_id = doc.metadata["idtopic"]
                elif doc.metadata["topic"] not in topic_code_to_id:
                    topic_id = (
                        await self.get_topic_by_code(doc.metadata["topic"])
                    ).idtopic
                    topic_code_to_id[doc.metadata["topic"]] = topic_id
                else:
                    topic_id = topic_code_to_id[doc.metadata["topic"]]
                if not topic_id:
                    logger.warning(
                        f"Topic ID not found for code {doc.metadata['topic']}. "
                        "Skipping chunk addition."
                    )
                    continue

                if "sub_doc_uuid" in doc.metadata:
                    subdocument_id = doc.metadata["sub_doc_uuid"]
                else:
                    subdocument_id = None

                if (
                    book_id,
                    language_code,
                    competence_id,
                ) not in self.book_lang_comp_chunks:
                    # turn off the previous chunks of the book, language and competence
                    await self.disable_chunks(
                        book_id, language_ids.get(language_code), competence_id
                    )
                    self.book_lang_comp_chunks.add(
                        (book_id, language_code, competence_id)
                    )

                await self.add_chunk(
                    cur,
                    ChunkDB(
                        idchunk=0,
                        content=doc.page_content,
                        embedding=embeddings[i],
                        idbook=book_id,
                        idlanguage=language_ids.get(language_code),
                        idcompetence=competence_id,
                        idtopic=topic_id,
                        idsubdocument=subdocument_id,
                        createdat=datetime.datetime.now(),
                        updatedat=datetime.datetime.now(),
                        enabled=True,
                    ),
                )

        await self.commit()
        logger.info(f"Added {len(docs)} chunks to the Vector DB.")

    async def get_learning_unit_translations_by_competence(
        self, idcompetence: int
    ) -> list[LearningUnitTranslationDB]:
        """Get all learning units for a specific competence."""
        query = """
            SELECT lut.*
            FROM learningunit lu
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            WHERE idconcept IN (
                SELECT idconcept
                FROM competenceconcept
                WHERE idcompetence = %s
                AND enabled = TRUE
            ) AND lu.enabled = TRUE
        """
        results = await self.fetchall(query, (idcompetence,))
        return (
            [
                LearningUnitTranslationDB(
                    idlearningunit=row[0],
                    idlanguage=row[1],
                    learninggoal=row[2],
                    task=row[3],
                    solution=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_concepts(self, topic_code: str) -> list[ConceptDB]:
        """Get all concepts."""
        query = """SELECT c.*
        FROM concept c 
        LEFT JOIN competenceconcept cc ON c.idconcept = cc.idconcept
        LEFT JOIN competence co ON cc.idcompetence = co.idcompetence
        LEFT JOIN topic t ON co.idtopic = t.idtopic
        WHERE t.code = %s AND c.enabled = TRUE"""
        results = await self.fetchall(query, (topic_code,))
        return (
            [
                ConceptDB(
                    idconcept=row[0],
                    createdat=row[1],
                    updatedat=row[2],
                    enabled=row[3],
                    code=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_concepts_for_competence_code(
        self, competence_code: str, locale: LocaleType
    ) -> list[ConceptTranslationJoinedDB]:
        """Get concepts for a specific competence."""
        query = """SELECT c.idconcept, l.idlanguage, c.code, ct.name, ct.description
            FROM competenceconcept cc
            LEFT JOIN concept c ON cc.idconcept = c.idconcept
            LEFT JOIN concepttranslation ct ON cc.idconcept = ct.idconcept
            LEFT JOIN competence co ON cc.idcompetence = co.idcompetence
            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE co.code = %s AND l.code = %s AND c.enabled = TRUE AND co.enabled = TRUE
        """
        concepts = await self.fetchall(query, (competence_code, locale.value))
        ret_concepts = []
        for concept_row in concepts:
            ret_concepts.append(
                ConceptTranslationJoinedDB(
                    idconcept=concept_row[0],
                    idlanguage=concept_row[1],
                    code=concept_row[2],
                    name=concept_row[3],
                    description=concept_row[4],
                )
            )

        return ret_concepts

    async def get_concepts_for_competence_code_all_languages(
        self, idcompetence: int
    ) -> list[ConceptTranslationMultiLanguage]:
        """Get concepts for a specific competence in all languages."""
        query = """SELECT c.idconcept, l.code, c.code, ct.name, ct.description
            FROM competenceconcept cc
            LEFT JOIN concept c ON cc.idconcept = c.idconcept
            LEFT JOIN concepttranslation ct ON cc.idconcept = ct.idconcept
            LEFT JOIN language l ON ct.idlanguage = l.idlanguage
            WHERE idcompetence = %s AND c.enabled = TRUE
        """
        concepts = await self.fetchall(query, (idcompetence,))
        ret = {}
        for row in concepts:
            if row[0] in ret:
                ret[row[0]].name[row[1]] = row[3]
                ret[row[0]].description[row[1]] = row[4]
            else:
                ret[row[0]] = ConceptTranslationMultiLanguage(
                    idconcept=row[0],
                    code=row[2],
                    name={row[1]: row[3]},
                    description={row[1]: row[4]},
                )

        return list(ret.values())

    async def get_learningunits_for_competence(
        self, idcompetence: int, idcompetencelevel: int, completed_luids: list[int]
    ) -> list[LearningUnitCombined]:
        """Get learning units for a specific competence and competence level."""
        query = """
            SELECT lu.idlearningunit, lu.idstep, lu.idcompetencelevel, lu.idconcept, l.idlanguage, l.code, lut.learninggoal, lut.task, lut.solution, lut.name, lu.code
            FROM learningunit lu
            LEFT JOIN concept c ON lu.idconcept = c.idconcept
            LEFT JOIN learningunittranslation lut ON lu.idlearningunit = lut.idlearningunit
            LEFT JOIN language l ON lut.idlanguage = l.idlanguage
            WHERE lu.idcompetencelevel = %s
            AND lu.idconcept IN (
                SELECT idconcept 
                FROM competenceconcept
                WHERE idcompetence = %s
            )
            AND lu.idlearningunit != ALL(%s)
            AND c.enabled = TRUE
        """
        learning_units = await self.fetchall(
            query, (idcompetencelevel, idcompetence, completed_luids)
        )
        ret_learning_units = []
        for lu_row in learning_units:
            ret_learning_units.append(
                LearningUnitCombined(
                    idlearningunit=lu_row[0],
                    idstep=lu_row[1],
                    idcompetencelevel=lu_row[2],
                    idconcept=lu_row[3],
                    idlanguage=lu_row[4],
                    language_code=lu_row[5],
                    learning_goal=lu_row[6],
                    task=lu_row[7],
                    solution=lu_row[8],
                    name=lu_row[9],
                    code=lu_row[10],
                )
            )

        return ret_learning_units

    async def get_config_value(self, key: str, environment: str) -> Optional[str]:
        """Get a configuration value by key."""
        query = "SELECT value FROM config WHERE key = %s AND environment = %s"
        result = await self.fetchone(query, (key, environment))
        return result[0] if result else None

    async def get_all_config_values(self, environment: str) -> dict[str, str]:
        """Get all configuration values for a given environment."""
        query = "SELECT key, value FROM config WHERE environment = %s"
        results = await self.fetchall(query, (environment,))
        return {row[0]: row[1] for row in results} if results else {}

    async def set_config_value(self, key: str, value: str, environment: str):
        """Set a configuration value by key."""
        if key is None:
            return  # nothing to do
        existing_value = await self.get_config_value(key, environment)
        if existing_value is not None:
            # Update existing record
            query = "UPDATE config SET value = %s WHERE key = %s AND environment = %s"
            await self.execute(query, (value, key, environment))
        else:
            # Insert new record
            query = "INSERT INTO config (key, value, environment) VALUES (%s, %s, %s)"
            await self.execute(query, (key, value, environment))

    async def get_purpose(self, code: str) -> Optional[PurposeDB]:
        """Get a purpose by its code."""
        query = "SELECT * FROM purposes WHERE code = %s AND enabled = TRUE"
        result = await self.fetchone(query, (code,))
        return (
            PurposeDB(
                idpurposes=result[0],
                code=result[1],
                icon=result[2],
                models=result[3],
                enabled=result[4],
            )
            if result
            else None
        )

    async def get_all_purposes(self) -> list[PurposeDB]:
        """Get all purposes."""
        query = "SELECT * FROM purposes WHERE enabled = TRUE"
        results = await self.fetchall(query)
        return (
            [
                PurposeDB(
                    idpurposes=row[0],
                    code=row[1],
                    icon=row[2],
                    models=row[3],
                    enabled=row[4],
                )
                for row in results
            ]
            if results
            else []
        )

    async def get_all_purposes_complete(self) -> list[PurposeCompleteDB]:
        """Get all purposes with translations for name and description."""
        query = """
            SELECT p.idpurposes, p.code, p.icon, p.models, p.enabled, l.code, pt.name, pt.description
            FROM purposes p
            LEFT JOIN purposestranslation pt ON p.idpurposes = pt.idpurposes
            LEFT JOIN language l ON pt.idlanguage = l.idlanguage
        """
        results = await self.fetchall(query)
        purposes_dict = {}
        for row in results:
            purpose_id = row[0]
            if purpose_id not in purposes_dict:
                purposes_dict[purpose_id] = PurposeCompleteDB(
                    idpurposes=row[0],
                    code=row[1],
                    icon=row[2],
                    models=row[3],
                    enabled=row[4],
                    name={LocaleType(row[5]): row[6]} if row[6] else {},
                    description={LocaleType(row[5]): row[7]} if row[7] else {},
                )
            language_code = row[5]
            if language_code and row[6]:
                purposes_dict[purpose_id].name[LocaleType(language_code)] = row[6]
            if language_code and row[7]:
                purposes_dict[purpose_id].description[LocaleType(language_code)] = row[7]
        return list(purposes_dict.values())

    async def update_purpose(self, purpose: PurposeDB) -> bool:
        """Update a purpose."""
        query = """
            UPDATE purposes
            SET icon = %s, models = %s, enabled = %s
            WHERE code = %s
        """
        try:
            await self.execute(
                query,
                (
                    purpose.icon,
                    purpose.models,
                    purpose.enabled,
                    purpose.code,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error updating purpose: {e}")
            await self.rollback()
            return False
    

    async def fix_topic_sequence(self):
        """Fix topic sequence."""
        query_seq = """
            SELECT pg_get_serial_sequence('topic', 'idtopic');
        """
        query_setval = """
            SELECT setval(%s, (SELECT COALESCE(MAX(idtopic), 0) FROM topic) + 1, false);
        """

        async with self.connection.cursor() as cursor:
            await cursor.execute(query_seq)
            seqname = (await cursor.fetchone())[0]
            await cursor.execute(query_setval, (seqname,))

    
    async def fix_book_sequence(self):
        """Fix book sequence."""
        query_seq = """
            SELECT pg_get_serial_sequence('book', 'idbook');
        """
        query_setval = """
            SELECT setval(%s, (SELECT COALESCE(MAX(idbook), 0) FROM book) + 1, false);
        """

        async with self.connection.cursor() as cursor:
            await cursor.execute(query_seq)
            seqname = (await cursor.fetchone())[0]
            await cursor.execute(query_setval, (seqname,))
    

    async def fix_competence_sequence(self):
        """Fix competence sequence."""
        query_seq = """
            SELECT pg_get_serial_sequence('competence', 'idcompetence');
        """
        query_setval = """
            SELECT setval(%s, (SELECT COALESCE(MAX(idcompetence), 0) FROM competence) + 1, false);
        """

        async with self.connection.cursor() as cursor:
            await cursor.execute(query_seq)
            seqname = (await cursor.fetchone())[0]
            await cursor.execute(query_setval, (seqname,))
    

    async def get_last_topic_id(self) -> int:
        """Get the last topic based on the highest idtopic."""
        query = """
        SELECT idtopic FROM topic ORDER BY idtopic DESC LIMIT 1
        """
        result = await self.fetchone(query)
        return result[0] if result else None
    

    async def get_last_competence_id(self) -> int:
        """Get the last competence ID based on the highest idcompetence."""
        query = """
        SELECT idcompetence FROM competence ORDER BY idcompetence DESC LIMIT 1
        """
        result = await self.fetchone(query)
        return result[0] if result else None


    async def get_last_book_id(self) -> int:
        """Get the last book based on the highest idbook."""
        query = """
        SELECT idbook FROM book ORDER BY idbook DESC LIMIT 1
        """
        result = await self.fetchone(query)
        return result[0] if result else None