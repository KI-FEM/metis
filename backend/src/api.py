import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).parent))
from bots.st.st_buddy import st_buddy
from framework.router import Router

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def validate_openapi_spec():
    """Check if OpenAPI scheme is up-to-date, if not, exit with error."""
    from generate_openapi import generate_api, get_api
    openapi_path = Path(__file__).parent.parent / 'openapi.json'
    if openapi_path.exists():
        with Path.open(Path(__file__).parent.parent / 'openapi.json') as f:
            try:
                file_spec = json.load(f)
                real_spec = get_api()
                if file_spec and file_spec != real_spec:
                    logger.info("OpenAPI schemas are different. Regenerating...")
                    generate_api(openapi_path)
            except json.JSONDecodeError:
                logger.info("OpenAPI schema is invalid. Regenerating...")
                generate_api(openapi_path)

logger.info("=====================================")
logger.info("Starting API server")
logger.info("=====================================")

app = FastAPI()

# Retrieve the allowed origins from the environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

# Configure CORS to allow multiple origins
app.add_middleware(CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bot_router = Router(app)

def register_bots():
    """Register all bots with the router."""
    bot_router.register_bot(st_buddy)

register_bots()

if os.getenv("GENERATE_OPENAPI") != "1":
    validate_openapi_spec()