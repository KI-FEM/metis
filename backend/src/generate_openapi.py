import json  # noqa: I001
import os
import sys
import subprocess
from pathlib import Path

from fastapi.openapi.utils import get_openapi


def get_api():
    """Get the OpenAPI schema from the FastAPI app."""
    os.environ["GENERATE_OPENAPI"] = "1"
    from api import app
    return get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            servers=app.servers,
        )


def generate_api(file: Path):
    """Write the OpenAPI schema to the given file."""
    with Path.open(file, 'w') as f:
        json.dump(get_api(), f, indent=4)

    print("OpenAPI schema generated successfully. Generating types...")
    if "TESTING" not in os.environ or \
        ("TESTING" in os.environ and os.environ["TESTING"] != "1"):
        try:
            proc = subprocess.run(["npm", "run", "types"], check=True, 
                    cwd=Path(__file__).parent.parent.parent / 'frontend')
            if proc.returncode == 0:
                print("Types generated successfully.")
            else:
                print("Error generating types.")
        except FileNotFoundError as e:
            print(f"OpenAPI scheme mismatch! TypeScript types could not be generated. "
                f"Please generate the types locally and commit them manually. {e}")
            sys.exit(1)

if __name__ == '__main__':
    openapi_path = Path(__file__).parent.parent / 'openapi.json'
    generate_api(openapi_path)
