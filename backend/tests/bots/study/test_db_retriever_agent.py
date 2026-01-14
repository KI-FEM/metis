import asyncio
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))

from bots.study.agents.db_retriever_agent import (
    execute_query,
    get_all_competences,
    get_concepts_for_competence_code,
    get_db_agent_prompt,
    get_relevant_learning_units,
    start_knowledge_graph_search,
)
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import LearnerModel, RequestModel
from framework.db.db_types import LightCompetenceTranslation

from ..database_mock import DatabaseMock
from ..prompt_patcher import PromptPatcher


class TestDBRetrieverAgent:
    """Test class for the DB Retriever Agent tools and functions."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return DatabaseMock()

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        return RequestModel(
            id="123",
            language="en",
            chat_history=[],
            response_preferences={
                "detail": 1,
                "illustration": 4,
                "language_style": 4,
                "humour": 2,
                "creativity": 1,
                "emojis": 3,
            },
            storage={
                "learner_model": LearnerModel(
                    competences={
                        "competence_1": {
                            "competence_id": 1,
                            "competence_code": "competence_1",
                            "completed": False,
                            "competence_level": 1,
                            "name": {
                                "en": "Resilience",
                                "de": "Resilienz",
                            },
                            "concepts": {
                                "concept_1": {
                                    "concept_id": 1,
                                    "concept_code": "concept_1",
                                    "completed": False,
                                    "custom_learning_goals": "",
                                    "name": {
                                        "en": "Concept 1",
                                        "de": "Konzept 1",
                                    },
                                    "learning_units": {
                                        "LU_create_resilience_example": {
                                            "id": 69,
                                            "code": "LU_create_resilience_example",
                                            "name": {
                                                "en": "Create Resilience Example",
                                                "de": "Erstelle Resilienz Beispiel",
                                            },
                                            "times_seen": 5,
                                            "last_seen": None,
                                            "times_quizzed": 0,
                                            "times_correct": 0,
                                            "last_quizzed": None,
                                            "completed": False,
                                        },
                                        "LU_completed": {
                                            "id": 1,
                                            "code": "LU_completed",
                                            "name": {
                                                "en": "Create Resilience Example",
                                                "de": "Erstelle Resilienz Beispiel",
                                            },
                                            "times_seen": 5,
                                            "last_seen": None,
                                            "times_quizzed": 0,
                                            "times_correct": 0,
                                            "last_quizzed": None,
                                            "completed": True,
                                        }
                                    },
                                }
                            },
                        }
                    }
                ),
                "selected_competence": "resilience",
                "chat_id": "test_chat_123",
                "unique_id": "test_unique_123",
            },
        )

    @pytest.fixture
    def mock_config(self, mock_db, mock_request):
        """Create a mock config for tools."""
        queue = asyncio.Queue()
        return {
            "configurable": {
                "queue": queue,
                "db": mock_db,
                "request": mock_request,
                "locale": LocaleType.EN,
            }
        }

    @pytest.mark.asyncio
    async def test_start_knowledge_graph_search_success(
        self, mocker, mock_config, mock_db, mock_request
    ):
        """Test the start_knowledge_graph_search tool with successful execution."""
        search_task = "Find all learning units for resilience level 1"

        # Mock the start_db_agent to return a successful response
        mock_agent_response = {
            "messages": [
                type(
                    "MockMessage",
                    (),
                    {
                        "content": (
                            "Found 5 learning units for resilience level "
                            "1:\n1. Learning Unit 1\n2. Learning Unit 2..."
                        )
                    },
                )()
            ]
        }
        mocker.patch(
            "bots.study.agents.db_retriever_agent.start_db_agent",
            return_value=mock_agent_response,
        )

        result = await start_knowledge_graph_search.ainvoke(
            input={
                "search_task": search_task,
            },
            config=mock_config,
        )

        # Verify the result contains the task and response
        assert "Task:" in result
        assert search_task in result
        assert "Response:" in result
        assert "Found 5 learning units" in result

        # Verify an event was put in the queue
        queue = mock_config["configurable"]["queue"]
        event_chunk = await queue.get()
        assert "info:" in event_chunk
        assert "start_knowledge_graph_search" in event_chunk

    @pytest.mark.asyncio
    async def test_start_knowledge_graph_search_error(
        self, mocker, mock_config, mock_db, mock_request
    ):
        """Test the start_knowledge_graph_search tool with error response."""
        search_task = "Invalid search task"

        # Mock the start_db_agent to return an error string
        error_message = "Error: The agent reached the maximum number of iterations"
        mocker.patch(
            "bots.study.agents.db_retriever_agent.start_db_agent",
            return_value=error_message,
        )

        result = await start_knowledge_graph_search.ainvoke(
            input={
                "search_task": search_task,
            },
            config=mock_config,
        )

        # Verify the error message is in the result
        assert "Task:" in result
        assert search_task in result
        assert "Response:" in result
        assert error_message in result

    @pytest.mark.asyncio
    async def test_get_relevant_learning_units_by_competence(
        self,
        mocker,
        mock_config,
    ):
        """Test get_relevant_learning_units tool filtering by competence_code."""
        result = await get_relevant_learning_units.ainvoke(
            input={
                "competence_level": 1,
                "competence_code": "resilience",
                "uncompleted_only": True,
                "localization": LocaleType.EN,
            },
            config=mock_config,
        )

        # Verify the result contains learning units
        assert "Retrieved Learning Units:" in result
        assert "LU_create_resilience_example" in result or "Lerneinheit" in result

        # Verify an event was put in the queue
        queue = mock_config["configurable"]["queue"]
        event_chunk = await queue.get()
        assert "info:" in event_chunk
        assert "get_relevant_learning_units" in event_chunk

    @pytest.mark.asyncio
    async def test_get_relevant_learning_units_by_concept(
        self, mocker, mock_config, mock_db
    ):
        """Test get_relevant_learning_units tool filtering by concept_code."""
        result = await get_relevant_learning_units.ainvoke(
            input={
                "competence_level": 2,
                "concept_code": "concept_1",
                "uncompleted_only": False,
                "completed_only": True,
                "localization": LocaleType.DE,
            },
            config=mock_config,
        )

        # Verify the result contains learning units
        assert "Retrieved Learning Units:" in result

        # Verify an event was put in the queue
        queue = mock_config["configurable"]["queue"]
        event_chunk = await queue.get()
        assert "info:" in event_chunk
        assert "get_relevant_learning_units" in event_chunk

    @pytest.mark.asyncio
    async def test_get_relevant_learning_units_uncompleted_only(
        self, mocker, mock_config, mock_db
    ):
        """Test get_relevant_learning_units filtering out completed units."""
        from framework.db.db_types import LearningUnitCombined

        mocker.patch.object(
            mock_db,
            "get_competence_by_code",
            return_value=type("Competence", (), {"idcompetence": 1})(),
        )

        # Track the call to verify completed_luids were excluded
        async def mock_get_lus(
            competence_id,
            competence_level_id,
            locale,
            excluded_luids=None,
            only_luids=None,
        ):
            # Verify that learning unit 1 (completed) is in excluded list
            assert excluded_luids is not None
            assert 1 in excluded_luids
            # Return mock data directly instead of calling the method again
            return [
                LearningUnitCombined(
                    idlearningunit=2,
                    idstep=1,
                    idcompetencelevel=competence_level_id,
                    idconcept=1,
                    idlanguage=1,
                    language_code="en",
                    learning_goal="Learning Goal 2",
                    task="Task 2",
                    solution="Solution 2",
                    name="Learning Unit 2",
                    code="LU_understand_resilience_concept",
                )
            ]

        mocker.patch.object(
            mock_db,
            "get_learning_units_for_competence_and_level",
            side_effect=mock_get_lus,
        )

        result = await get_relevant_learning_units.ainvoke(
            input={
                "competence_level": 1,
                "competence_code": "resilience",
                "uncompleted_only": True,
                "localization": LocaleType.EN,
            },
            config=mock_config,
        )

        assert "Retrieved Learning Units:" in result
        # Verify the uncompleted unit is in the result
        assert "LU_understand_resilience_concept" in result

    @pytest.mark.asyncio
    async def test_execute_query_select_success(self, mocker, mock_config, mock_db):
        """Test execute_query tool with successful SELECT query."""
        query = "SELECT * FROM competence WHERE code = 'resilience'"
        mock_results = [
            {"idcompetence": 1, "code": "resilience", "name": "Resilience"},
            {"idcompetence": 2, "code": "self_efficacy", "name": "Self-Efficacy"},
        ]

        mocker.patch.object(
            mock_db,
            "execute",
            return_value=mock_results,
        )

        result = await execute_query.ainvoke(
            input={
                "goal": "Retrieve resilience competence information",
                "reasoning": "I need to get the competence details from the database",
                "query": query,
            },
            config=mock_config,
        )

        # Verify the result contains the query and results
        assert "Query executed successfully" in result
        assert query in result
        assert "Results:" in result
        assert "resilience" in result
        assert "Self-Efficacy" in result

    @pytest.mark.asyncio
    async def test_execute_query_select_no_results(self, mocker, mock_config, mock_db):
        """Test execute_query tool with SELECT query returning no results."""
        query = "SELECT * FROM competence WHERE code = 'nonexistent'"

        mocker.patch.object(
            mock_db,
            "execute",
            return_value=[],
        )

        result = await execute_query.ainvoke(
            input={
                "goal": "Find nonexistent competence",
                "reasoning": "Testing query with no results",
                "query": query,
            },
            config=mock_config,
        )

        # Verify the result indicates no results found
        assert "Query executed successfully" in result
        assert "no results were found" in result

    @pytest.mark.asyncio
    async def test_execute_query_non_select_rejected(
        self, mocker, mock_config, mock_db
    ):
        """Test execute_query tool rejects non-SELECT queries."""
        query = "DELETE FROM competence WHERE code = 'test'"

        result = await execute_query.ainvoke(
            input={
                "goal": "Delete data",
                "reasoning": "Attempting unauthorized operation",
                "query": query,
            },
            config=mock_config,
        )

        # Verify the query was rejected
        assert "Error: Only SELECT queries are allowed" in result

    @pytest.mark.asyncio
    async def test_execute_query_database_error(self, mocker, mock_config, mock_db):
        """Test execute_query tool handles database errors."""
        query = "SELECT * FROM invalid_table"

        mocker.patch.object(
            mock_db,
            "execute",
            side_effect=Exception("Table does not exist"),
        )

        result = await execute_query.ainvoke(
            input={
                "goal": "Query invalid table",
                "reasoning": "Testing error handling",
                "query": query,
            },
            config=mock_config,
        )

        # Verify the error is in the result
        assert "Error executing query" in result
        assert "Table does not exist" in result

    @pytest.mark.asyncio
    async def test_execute_query_tuple_results(self, mocker, mock_config, mock_db):
        """Test execute_query tool with tuple results instead of dict."""
        query = "SELECT code, name FROM competence"
        mock_results = [
            ("resilience", "Resilience"),
            ("self_efficacy", "Self-Efficacy"),
        ]

        mocker.patch.object(
            mock_db,
            "execute",
            return_value=mock_results,
        )

        result = await execute_query.ainvoke(
            input={
                "goal": "Get competence codes and names",
                "reasoning": "Simple query returning tuples",
                "query": query,
            },
            config=mock_config,
        )

        # Verify the result is formatted as a table
        assert "Query executed successfully" in result
        assert "Row | Values" in result
        assert "resilience" in result
        assert "Self-Efficacy" in result

    @pytest.mark.asyncio
    async def test_get_all_competences_success(self, mocker, mock_config, mock_db):
        """Test get_all_competences tool returns all competences."""
        mock_competences = [
            LightCompetenceTranslation(
                idcompetence=1,
                code="resilience",
                name="Resilience",
                description="The ability to bounce back from adversity",
                language_code="en",
            ),
            LightCompetenceTranslation(
                idcompetence=2,
                code="self_efficacy",
                name="Self-Efficacy",
                description="Belief in one's ability to succeed",
                language_code="en",
            ),
        ]

        mocker.patch.object(
            mock_db,
            "get_competences_translated_light",
            return_value=mock_competences,
        )

        result = await get_all_competences.ainvoke(
            input={},
            config=mock_config,
        )

        # Verify the result contains all competences
        assert "Retrieved 2 competences:" in result
        assert "resilience" in result
        assert "Resilience" in result
        assert "The ability to bounce back" in result
        assert "self_efficacy" in result
        assert "Self-Efficacy" in result

    @pytest.mark.asyncio
    async def test_get_all_competences_empty(self, mocker, mock_config, mock_db):
        """Test get_all_competences tool when no competences exist."""
        mocker.patch.object(
            mock_db,
            "get_competences_translated_light",
            return_value=[],
        )

        result = await get_all_competences.ainvoke(
            input={},
            config=mock_config,
        )

        # Verify the result indicates no competences
        assert "Retrieved 0 competences:" in result

    @pytest.mark.asyncio
    async def test_get_concepts_for_competence_code_success(
        self, mocker, mock_config, mock_db
    ):
        """Test get_concepts_for_competence_code tool returns concepts."""
        result = await get_concepts_for_competence_code.ainvoke(
            input={
                "competence_code": "resilience",
            },
            config=mock_config,
        )

        # Verify the result contains all concepts
        assert "Retrieved 2 concepts for competence code resilience:" in result
        assert "Personal Resilience" in result
        assert "Individual resilience factors" in result
        assert "Social Context" in result

    @pytest.mark.asyncio
    async def test_get_concepts_for_competence_code_not_found(
        self, mocker, mock_config, mock_db
    ):
        """Test get_concepts_for_competence_code tool when no concepts found."""
        mocker.patch.object(
            mock_db,
            "get_concepts_for_competence_code",
            return_value=[],
        )

        result = await get_concepts_for_competence_code.ainvoke(
            input={
                "competence_code": "nonexistent",
            },
            config=mock_config,
        )

        # Verify the result indicates no concepts found
        assert "No concepts found for competence code nonexistent" in result

    @pytest.mark.asyncio
    async def test_get_db_agent_prompt(self, mocker, mock_request, mock_db):
        """Test get_db_agent_prompt function."""
        agent_task = "Find all learning units for resilience"

        # Mock the langfuse prompt
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": (
                        "You are a database agent.\n"
                        "Task: {{task}}\n"
                        "Database Schema: {{database_schema}}\n"
                        "Learner Model: {{learner_model}}"
                    ),
                    "role": "system",
                }
            ],
            name="competence-db-agent-en",
        ).patch(mocker)

        # Mock the DB schema
        mock_schema = '{"tables": ["competence", "concept", "learning_unit"]}'
        mocker.patch(
            "bots.study.agents.db_retriever_agent.read_db_schema",
            return_value=mock_schema,
        )

        result = await get_db_agent_prompt(mock_request, mock_db, agent_task)

        # Verify the result is a system message
        assert result.content is not None
        assert "You are a database agent" in result.content
        assert agent_task in result.content
        assert mock_schema in result.content

    @pytest.mark.asyncio
    async def test_get_db_agent_prompt_with_learner_model(
        self, mocker, mock_request, mock_db
    ):
        """Test get_db_agent_prompt includes learner model information."""
        agent_task = "Find uncompleted learning units"

        # Mock the langfuse prompt
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "Task: {{task}}\nLearner Model: {{learner_model}}",
                    "role": "system",
                }
            ],
            name="competence-db-agent-en",
        ).patch(mocker)

        # Mock read_db_schema
        mocker.patch(
            "bots.study.agents.db_retriever_agent.read_db_schema",
            return_value="{}",
        )

        result = await get_db_agent_prompt(mock_request, mock_db, agent_task)

        # Verify learner model is in the prompt
        assert result.content is not None
        assert "concept_1" in result.content or "Learner Model" in result.content

    @pytest.mark.asyncio
    async def test_get_db_agent_prompt_different_locale(
        self, mocker, mock_request, mock_db
    ):
        """Test get_db_agent_prompt with different locale."""
        # Mock the locale method to return German
        mocker.patch(
            "framework.api_types.request_format.RequestModel.locale",
            return_value=LocaleType.DE,
        )
        agent_task = "Finde alle Lerneinheiten"

        # Mock the German langfuse prompt
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "Sie sind ein Datenbank-Agent.\nAufgabe: {{task}}",
                    "role": "system",
                }
            ],
            name="competence-db-agent-de",
        ).patch(mocker)

        # Mock read_db_schema
        mocker.patch(
            "bots.study.agents.db_retriever_agent.read_db_schema",
            return_value="{}",
        )

        result = await get_db_agent_prompt(mock_request, mock_db, agent_task)

        # Verify German prompt is used
        assert result.content is not None
        assert "Sie sind ein Datenbank-Agent" in result.content
        assert agent_task in result.content
