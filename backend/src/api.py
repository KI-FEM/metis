import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langfuse import Langfuse

sys.path.append(str(Path(__file__).parent))
import bots
from bots.scads.scads_factory import create_scads_bots_sync
from framework.prometheus_fastapi_instrumentator import Instrumentator, metrics
from framework.router import Router
from framework.router_dev import RouterDev

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Filter out health check and metrics requests from uvicorn access logs
class HealthCheckFilter(logging.Filter):
    """Filter to exclude health check and metrics endpoints from logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for health check requests to exclude them from logs."""
        message = record.getMessage()
        return not any(
            endpoint in message for endpoint in ["/health", "/health/ready", "/metrics"]
        )


# Apply filter to uvicorn access logger
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(HealthCheckFilter())


def validate_openapi_spec():
    """Check if OpenAPI scheme is up-to-date, if not, exit with error."""
    from generate_openapi import generate_api, get_api

    openapi_path = Path(__file__).parent.parent / "openapi.json"
    if openapi_path.exists():
        with Path.open(Path(__file__).parent.parent / "openapi.json") as f:
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

# Set up Prometheus instrumentation
instrumentator = Instrumentator()

# Add extra metrics
instrumentator.add(metrics.latency(buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]))
instrumentator.add(metrics.requests())
instrumentator.add(metrics.combined_size())

# Instrument the app
instrumentator.instrument(app).expose(app)

# Retrieve the allowed origins from the environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

# Configure CORS to allow multiple origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


bot_router = Router(app)
dev_router = RouterDev(app)
app.include_router(dev_router.get_router())
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

# create Langfuse client to be retrieved using get_client() later
langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
    environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT"),
)


def register_bots():
    """Register all bots with the router."""
    # Register dynamic ScaDS.AI assistant bots
    scads_bots = create_scads_bots_sync()
    for bot in scads_bots:
        bot_router.register_bot(bot)
    logger.info(f"Registered {len(scads_bots)} ScaDS.AI assistant bots")
    
    # Register static bots
    bot_router.register_bot(bots.passthrough_bot)
    bot_router.register_bot(bots.study_competence_bot)
    bot_router.register_bot(bots.st_buddy)
    bot_router.register_bot(bots.grumci_buddy)
    bot_router.register_bot(bots.tokenius)
    bot_router.register_bot(bots.dissy)


register_bots()


if os.getenv("GENERATE_OPENAPI") != "1":
    validate_openapi_spec()
