from pathlib import Path

from rich import print as richprint
from rich.markup import escape
from rich.tree import Tree


def walk_directory(directory: Path, tree: Tree) -> None:    
    """Recursively build a Tree with directory contents."""
    # Sort dirs first then by filename
    paths = sorted(
        Path(directory).iterdir(),
        key=lambda path: (path.is_dir(), path.name.lower()),
    )
    for path in paths:
        # Remove hidden files
        if path.name.startswith(".") or path.name.startswith("__"):
            continue
        if path.is_dir():
            style = ""
            tree.add(
                f"[bold magenta]:open_file_folder: [link file://{path}]{escape(path.name)}",
                style=style,
                guide_style=style,
            )
    richprint(tree)
