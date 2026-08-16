from fastapi import APIRouter

from app.api.routes.control_tower import router as control_tower_router
from app.api.routes.health import router as health_router
from app.api.routes.opportunity import router as opportunity_router
from app.api.routes.regulations import router as regulations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(control_tower_router)
api_router.include_router(opportunity_router)
api_router.include_router(regulations_router)
