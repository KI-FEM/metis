# pragma: exclude file

import os
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))
from framework.db.database import Database


class RouterDev:
    """Router for dev purposes, such as database management."""

    def __init__(self, app: FastAPI):
        """Initialize the RouterDev with the FastAPI app."""
        self.app = app
        self.router = app.router
        self.db = Database()
        environment = os.getenv("ENVIRONMENT", "development")
        self.enabled = environment == "development"
        self.router = APIRouter(prefix="/dev")

        class DevResponse(BaseModel):
            success: bool
            message: str
            data: dict = None

        def check_enabled():
            """Check if the dev routes are enabled."""
            if not self.enabled:
                raise ValueError("Dev routes are not enabled in this environment")
        
        @self.router.get("/db/schema/drop")
        async def drop_schema() -> DevResponse:
            check_enabled()
            if not self.db.connection:
                return {"success": False, "message": "Database not connected"}
            await self.db.drop_schema()
            return {"success": True, "message": "Schema dropped"}

        @self.router.get("/db/schema/create")
        async def create_schema() -> DevResponse:
            check_enabled()
            if not self.db.connection:
                return {"success": False, "message": "Database not connected"}
            await self.db.create_schema()
            return {"success": True, "message": "Schema created"}

        @self.router.get("/db/schema/load")
        async def load_schema() -> DevResponse:
            check_enabled()
            if not self.db.connection:
                return {"success": False, "message": "Database not connected"}
            await self.db.load_schema()
            return {"success": True, "message": "Schema loaded"}

        @self.router.get("/db/data/load")
        async def load_data() -> DevResponse:
            check_enabled()
            if not self.db.connection:
                return {"success": False, "message": "Database not connected"}
            await self.db.load_data()
            return {"success": True, "message": "Data loaded"}

        @self.router.get("/db/schema/valid")
        async def get_schema() -> DevResponse:
            check_enabled()
            if not self.db.connection:
                return {"success": False, "message": "Database not connected"}
            schema = await self.db.schema_exists()
            return {
                "success": True,
                "message": f"Schema exists: {schema}",
                "data": {"schema_exists": schema},
            }

        @self.router.get("/db/connect")
        async def connect_db() -> DevResponse:
            check_enabled()
            if self.db.connection:
                return {"success": True, "message": "Already connected to the database"}
            try:
                await self.db.connect()
                db_info = await self.db.get_db_info()
                return {
                    "success": True,
                    "message": "Database info retrieved",
                    "data": db_info,
                }
            except Exception as e:
                return {"success": False, "message": str(e)}

    def get_router(self):
        """Return the router for the dev routes."""
        return self.router
