import ast
import asyncio
import logging
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.tree import Tree

sys.path.append(str(Path(__file__).parent.parent))
from bot_duplication import cli_representation, helpers
from framework.db.database import Database
from framework.db.db_types import (
    BookDB,
    CompetenceDB,
    TopicDB,
)

BOTS_PATH = Path(__file__).parent.parent / "bots"
DATA_PATH = Path(__file__).parent.parent.parent / "data"
TEST_PATH = Path(__file__).parent.parent.parent / "tests" / "bots"

API_PATH = Path(__file__).parent.parent / "api.py"
INGESTER_PATH = Path(__file__).parent.parent / "module_loading"/"ingester.py"
TOPIC_PATH = Path(__file__).parent.parent / "framework"/"api_types"/"topics.py"

# TODO: - rewriting of LocalizedStrings, for easier duplication process
# TODO: - extend test_bots_have_tests with new bot
# TODO: - CLI representation 



logger = logging.getLogger()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


async def duplicate_directory(data_directory: Path) -> None:
    """Duplicate an directory and create new one."""
    logger.info("These are the current available bots:")

    tree = Tree(
        f":open_file_folder: [link file:{BOTS_PATH.name}",
        guide_style="bold bright_blue",
    )
    cli_representation.walk_directory(BOTS_PATH, tree)

    source = helpers.get_valid_input(
        "Which bot would you like to copy? (Copying Tokenius is recommended) ",
        lambda x: (BOTS_PATH / x).is_dir()
    )
    source_bot_path = (BOTS_PATH / source).resolve()
    target = helpers.get_valid_input(
        "Name of the new bot: ",
        lambda x: not (BOTS_PATH / x).exists()
    )
    target_bot_path = (BOTS_PATH / target).resolve()

    try:
        shutil.copytree(source_bot_path, target_bot_path)
        logger.info(
            "Successfully copied bot from '%s' to '%s'.", 
            source_bot_path, 
            target_bot_path
        )
    except FileExistsError as e:
        logger.error("Failed to copy directory: %s", e)
        raise

    source_bot_name = source_bot_path.stem
    target_bot_name = target_bot_path.stem

    create_new_test_bot(source_bot_name, target_bot_name)

    rewriting_code = helpers.get_valid_input(
        prompt="Should the code be automatically refactored?: [y/n] ",
        validator=helpers.is_yes_no
    )

    if rewriting_code == "y":
        logger.info("Starting automatic code refactoring for '%s'.", target)
        refactor_source_code(source_bot_name, target_bot_name)
        extend_topic_file(target_bot_path)
        extend_bot_init(target_bot_path)
        extend_api_file(target_bot_path)
        logger.info("Code refactoring completed for '%s'.", target)
    else : 
        logger.info("Rewriting of source code skipped.")
    
    extending_db = helpers.get_valid_input(
        "Create all necessary rows in database?: [y/n] ",
        helpers.is_yes_no                                 
    )

    if extending_db == "y":
        logger.info("Extending database for '%s'.", target)
        await extend_db(data_directory)
        logger.info("Database extension compelete for '%s'.", target)
    else:
        logger.info("Database is not updated with new rows.")


def refactor_source_code(source_bot_name: str, target_bot_name: str) -> None:
    """Read the code of source file and change."""
    main_paths: list[Path] = [BOTS_PATH, TEST_PATH]
    for main_path in main_paths:
        for file_path in (main_path / target_bot_name).rglob("*.py"):
            new_content = []
            content = helpers.read_file_lines(file_path)
            for line in content:
                if re.search(f"{source_bot_name}", line, flags=re.IGNORECASE):
                    line = helpers.handle_case_sensitivity(
                        line,
                        source_bot_name,
                        target_bot_name
                    )
                new_content.append(line)
            helpers.write_file_lines(file_path, new_content)
        

async def extend_db(target_data_path: Path) -> None:
    """Create new rows for tables topic, competence and book in the metis database."""
    db = Database()
    await db.connect()
    await db.fix_topic_sequence()
    # 1. add Topic 
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    new_topic = TopicDB(
        idtopic= await db.get_last_topic_id() + 1,
        code=target_data_path.stem,
        createdat=current_date,
        updatedat=current_date,
        enabled=True
    )
    topic_id = await db.add_topic(new_topic)

    # 2. add Competence
    all_competences_rel = [
        subdir.relative_to(DATA_PATH)
        for subdir in target_data_path.rglob("*/")
        if len(subdir.relative_to(DATA_PATH).parts) < 4
        ]
    all_competence_names = set()
    await db.fix_competence_sequence()
    for competence in all_competences_rel:
        if len(competence.parts) < 3:
            continue

        new_competence = CompetenceDB(
            idcompetence=await db.get_last_competence_id() + 1,
            createdat=current_date,
            updatedat=current_date,
            enabled=True,
            code=competence.stem,
            idtopic=topic_id
        )
        all_competence_names.add(new_competence.code)
        await db.add_competence(new_competence)

    # 3. add Book
    await db.fix_book_sequence()

    all_books_rel = [
        subdir.relative_to(DATA_PATH)
        for subdir in target_data_path.rglob("*") 
        if subdir.is_dir()
    ]

    all_book_names = set()
    for book in all_books_rel:
        if len(book.parts) < 3:
            continue

        languages = await db.get_languages_by_locale()
        for language in languages:
            if language == book.parts[1]:
                language_id = languages[language].idlanguage

        new_book = BookDB(
            idbook=await db.get_last_book_id() + 1,
            title=book.stem,
            idlanguage=language_id,
            createdat=current_date,
            updatedat=current_date,
            enabled=True,
            authors=None,
            code=book.stem
        )
        all_book_names.add(new_book.code)
        await db.add_book(new_book)

    extend_metadata(
        competence_names=all_competence_names,
        book_names=all_book_names,
        topic_name=new_topic.code
    )


def create_data_directory() -> None:
    """Create a data_directory where all the Markdown-Files are stored."""
    valid_user_input = helpers.get_valid_input(
        "Create new data directories for new bot?: [y/n] ",
        helpers.is_yes_no
    )
    if valid_user_input == "y":
        new_module = input("What should be the name of your new data folder?: ")
        try:
            return helpers.create_module_structure(new_module, DATA_PATH)
        except FileExistsError as e:
            raise FileExistsError(f"Directory already exists: {e}")

    elif valid_user_input == "n":
        logger.info(
            "Please provide a name for the directory, " \
            "otherwise this version of the tool will not work."
        )
        user_input = helpers.get_valid_input(
            "Please create a directory and provide the name of your data folder: ",
            lambda x: not (DATA_PATH / x).exists()
        )
        if not user_input:
            raise ValueError(
                "If no data directory is provided the setup can't be completed"
            )
        
        try:
            return helpers.create_module_structure(user_input, DATA_PATH)
        except Exception as e:
            raise Exception(f"Error creating directory structure: {e}")


def extend_topic_file(directory: Path) -> None:
    """Extends the topica.py file, so the chatbot has a new identifier."""
    content = helpers.read_file(TOPIC_PATH)
    module = ast.parse(content)
    topic_node = None
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "Topic":
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            if "Enum" in bases:
                topic_node = node
                break
    if topic_node is None:
        raise RuntimeError("No class Topic(Enum) was found.")
    start = topic_node.lineno  
    end = topic_node.end_lineno
    if end is None:
        raise RuntimeError("Requires Python 3.8+ for end_lineno-support.")

    lines = content.splitlines(keepends=True)
    indent = "    " 
    for i in range(start, end): 
        line = lines[i].rstrip("\n")
        if line.strip(): 
            leading = line[:len(line) - len(line.lstrip())]
            if leading:
                indent = leading
            break
    new_assignment = f"{indent}{directory.stem} = \"{directory.stem}\"\n"
    insert_index = end  
    new_lines = lines[:insert_index] + [new_assignment] + lines[insert_index:]
    new_content = "".join(new_lines)
    helpers.write_file(TOPIC_PATH, new_content)


def extend_api_file(target_bot_path: Path) -> None:
    """Automatically register the new bot in the api.py file."""  
    content = helpers.read_file(API_PATH)
    module = ast.parse(content)
    target_function = None 
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "register_bots":
            target_function = node
            break
    if target_function is None:
        raise RuntimeError("Function not found.")
    start = target_function.lineno
    end = target_function.end_lineno
    lines = content.splitlines(keepends=True)
    indent = None
    for i in range(start, end):
        stripped = lines[i].strip()
        if stripped:
            leading = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            if leading:
                indent = leading
            break
    if indent is None:
        indent = "    "
    
    new_code = f"{indent}bot_router.register_bot(bots.{target_bot_path.stem})\n"
    insert_index = end
    new_lines = lines[:insert_index] + [new_code] + lines[insert_index:]
    new_content = "".join(new_lines)
    helpers.write_file(API_PATH, new_content)

# TODO: if-else structure: books missing
def extend_metadata(competence_names: set[str],
                     book_names: set[str], 
                     topic_name: str) -> None:
    """Extend the metadata for ingesting in set_doc_metadata in file ingester."""
    content = helpers.read_file(INGESTER_PATH)
    module = ast.parse(content)

    target_statement = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "set_doc_metadata":
            for inner_node in node.body:
                if isinstance(inner_node, ast.If):
                    test = inner_node.test
                    if helpers.validate_if_statement(test):
                        target_statement = inner_node
                        break
    
    if target_statement is None:
        raise RuntimeError("If-Statement not found.")
    
    end = target_statement.end_lineno
    lines = content.splitlines(keepends=True)
    indent = "    "
    new_content =  f"{indent}elif topic == '{topic_name}':\n"
    for index, name in enumerate(competence_names):
        if index == 0:
            new_content += f"{indent * 2}if competence == '{name}':\n"
        else:
            new_content += f"{indent * 2}elif competence == '{name}':\n"
        new_content += f"{indent * 3}book_code = '{name}'\n"

    new_lines = lines[:end] + [new_content]  + lines[end:]
    new_content = "".join(new_lines)
    helpers.write_file(INGESTER_PATH, new_content)
    

def extend_bot_init(target_bot_path: Path):
    """Extend import statements to be registered in api."""
    helpers.extend_file(
        file_path=BOTS_PATH / "__init__.py", 
        new_content=(
            f"\nfrom bots.{target_bot_path.stem}.chatbot import {target_bot_path.stem}"
        )
    )

    file_content = helpers.read_file(BOTS_PATH/"__init__.py")
    ast_parse = ast.parse(file_content)

    for node in ast_parse.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "__all__":
            end = node.value.end_lineno
            break
    indent = "    "
    lines = file_content.splitlines(keepends=True)
    new_lines= (lines[:end - 1] + 
                   [f"{indent}'{target_bot_path.stem}',\n"] + 
                   lines[end - 1:]
    )
    new_content = "".join(new_lines)
    helpers.write_file(BOTS_PATH/"__init__.py", new_content)
            

def create_new_test_bot(source_bot_name: str, target_bot_name: str):
    """Copy test bot directory for new bot."""
    source_bot_path = TEST_PATH / source_bot_name
    target_bot_path = TEST_PATH / target_bot_name

    try:
        shutil.copytree(source_bot_path, target_bot_path)
        logger.info(
            "Successfully copied bot from '%s' to '%s'.", 
            source_bot_path, 
            target_bot_path
        )
    except FileExistsError as e:
        logger.error("Failed to copy directory: %s", e)
        raise


async def copy_new_bot():
    """Interface function for copying a bot."""
    data_directory = create_data_directory()

    if data_directory:
        await duplicate_directory(data_directory)
    else:
        logger.error("Data directory could not be created.")
    

if __name__=="__main__":
    import platform

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(copy_new_bot())