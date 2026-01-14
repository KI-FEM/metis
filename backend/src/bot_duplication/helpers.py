import ast
import sys
from pathlib import Path
from typing import Callable

sys.path.append(str(Path(__file__).parent.parent))
from framework.api_types.locale_type import LocaleType


def get_valid_input(prompt: str, validator: Callable[[str], bool]) -> str:
    """Prompt user for input and validate it using the provided validator function."""
    while True:
        user_input = input(prompt)
        if validator(user_input):
            return user_input
        print("Invalid input. Please try again.")


def is_yes_no(value: str) -> bool:
    """Validator for yes-no-questions."""
    return value.lower() in ("y", "n")


def read_file_lines(file_path: Path) -> str:
    """Read the file line per line."""
    with Path.open(file_path, "r") as file:
        return file.readlines()


def write_file_lines(file_path: Path, new_content: str):
    """Write the file line per line."""
    with Path.open(file_path, "w") as file:
        file.writelines(new_content)

def read_file(file_path: Path) -> str:
    """Read the file as one string."""
    with Path.open(file_path, "r") as file:
        return file.read()
    
def write_file(file_path: Path, new_content: bytes):
    """Write the file as one string."""
    with Path.open(file_path, "w") as file:
        file.write(new_content)


def extend_file(file_path: Path, new_content: str):
    """Extending the file and not rewriting it."""
    with Path.open(file_path, "a") as file:
        file.write(new_content)

            
def validate_if_statement(node_test: ast.If) -> bool:
    """Validate a specific if-statement in chatbot.py."""
    if (
    isinstance(node_test, ast.Compare)
    and isinstance(node_test.left, ast.Name)
    and node_test.left.id == "topic"
    and len(node_test.ops) == 1
    and isinstance(node_test.ops[0], ast.Eq)
    and len(node_test.comparators) == 1
    and isinstance(node_test.comparators[0], ast.Constant)
    and node_test.comparators[0].value == "study_competence"
    ):
        return True
    return False

def class_name_declaration(line_of_code: str, target_bot_name: str) -> str:
    """Changes Class-name and capitalize it."""
    module = ast.parse(line_of_code)

    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == f"{target_bot_name}":
            node.name = node.name.capitalize()
        if isinstance(node, ast.Assign) and node.targets[0].id == f"{target_bot_name}":
            if isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    node.value.func.id = node.value.func.id.capitalize()
                elif isinstance(node.value.func, ast.Attribute):
                    node.value.func.attr = node.value.func.attr.capitalize()
                else:
                    raise ValueError("Declaration not found.")
    return ast.unparse(module)

def handle_case_sensitivity(line_of_code: str, 
                            source_bot_name: str, 
                            target_bot_name: str) -> str:
    """Hanldes case sensitivity in chatbot.py."""
    if f"{source_bot_name.capitalize()}" in line_of_code:
        line_of_code = line_of_code.replace(
            f"{source_bot_name.capitalize()}", 
            f"{target_bot_name.capitalize()}"
        )
    if f"{source_bot_name.lower()}" in line_of_code:
        line_of_code = line_of_code.replace(
            f"{source_bot_name.lower()}", 
            f"{target_bot_name.lower()}"
        )
    if f"{source_bot_name.upper()}" in line_of_code:
        line_of_code = line_of_code.replace(
            f"{source_bot_name.upper()}", 
            f"{target_bot_name.upper()}"
        )
    return line_of_code


def create_module_structure(module_name: str, base_path: Path) -> Path:
    """Erstellt die Ordnerstruktur für ein Modul mit Sprach- und Kompetenzordnern.
    
    Args:
        module_name: Name des Moduls
        base_path: Basis-Pfad wo die Struktur erstellt werden soll
        
    Returns:
        Path zum erstellten Modul

    """
    module_path = (base_path / module_name).resolve()
    competence_types = ["_content", "_exercises", "_organizational"]
    language = input("Which language folders do you need?: [DE/EN/BOTH] ").upper()
    
    language_map = {
        "DE": [LocaleType.DE.value],
        "EN": [LocaleType.EN.value],
        "BOTH": [LocaleType.DE.value, LocaleType.EN.value]
    }
    
    if language not in language_map:
        raise ValueError(
            f"Invalid language option: {language}. Please choose DE, EN, or BOTH."
        )
    
    for lang in language_map[language]:
        for competence in competence_types:
            Path.mkdir(
                module_path / lang / f"{module_name}{competence}",
                exist_ok=False,
                parents=True
            )
    
    return base_path / module_name
