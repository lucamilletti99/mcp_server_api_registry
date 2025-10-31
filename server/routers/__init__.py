# Generic router module for the Databricks app template
# Add your FastAPI routes here

from fastapi import APIRouter

from .chat import router as chat_router
from .health import router as health_router
from .mcp_info import router as mcp_info_router
from .prompts import router as prompts_router
from .traces import router as traces_router
from .user import router as user_router
from .debug_auth import router as debug_auth_router

router = APIRouter()
router.include_router(user_router, prefix='/user', tags=['user'])
router.include_router(prompts_router, prefix='/prompts', tags=['prompts'])
router.include_router(mcp_info_router, prefix='/mcp_info', tags=['mcp'])
router.include_router(chat_router, prefix='/chat', tags=['chat'])
router.include_router(traces_router, prefix='/traces', tags=['traces'])
router.include_router(health_router, tags=['health'])
router.include_router(debug_auth_router, prefix='/debug', tags=['debug'])
