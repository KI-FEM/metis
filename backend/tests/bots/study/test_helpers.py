import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from bots.study.helpers.data_retriever import get_questions
from framework.api_types.locale_type import LocaleType
from src.generate_openapi import generate_api

TEST_DATA_DIR = Path(__file__).parent / "test_data"

def test_get_questions():
    """Test get_questions function."""
    questions = get_questions("study_competence", LocaleType.EN, module="resilience")
    assert isinstance(questions, list)
    assert len(questions) > 0
    assert all(isinstance(q, str) for q in questions)
    assert "What is resilience, and why is it important?" in questions

def test_generate_api(tmp_path):
    """Test generate_api function."""
    os.environ["TESTING"] = "1"
    dummy_file = tmp_path / "openapi.json"
    generate_api(dummy_file)
    
    assert dummy_file.exists(), "openapi.json file was not created."
    
    with Path.open(dummy_file, 'r') as f:
        data = json.load(f)
        assert isinstance(data, dict), "Generated file does not contain valid JSON."
    
    dummy_file.unlink()
    assert not dummy_file.exists(), "openapi.json file was not deleted."
