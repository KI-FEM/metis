import json
import os
import sys
from pathlib import Path

import nltk
import pytest

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from bots.study.helpers.data_retriever import get_headers
from src.generate_openapi import generate_api

if "NLTK_DATA" in os.environ:
    nltk.data.path.append(os.environ['NLTK_DATA'])

TEST_DATA_DIR = Path(__file__).parent / "test_data"

def test_get_headers():
    """Test get_headers function."""
    assert get_headers("markdown", "en", TEST_DATA_DIR) == {
        "markdown.md": ["Lorem Ipsum", "Section 1", "Subsection 1.1", "Subsection 1.2", 
                        "Section 2", "Conclusion"],
    }
    
def test_get_headers_no_folder():
    """Test get_headers function with non-existing folder."""
    with pytest.raises(FileNotFoundError) as e:
        get_headers("asdf", "en", TEST_DATA_DIR)
    assert e.value.__str__() == f"Topic folder 'asdf' not found in {TEST_DATA_DIR}/en"

def test_get_headers_no_files():
    """Test get_headers function with folder containing no files."""
    with pytest.raises(FileNotFoundError) as e:
        get_headers("no_files", "en", TEST_DATA_DIR)
    assert e.value.__str__() == "No markdown files found in topic folder 'no_files'"

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
