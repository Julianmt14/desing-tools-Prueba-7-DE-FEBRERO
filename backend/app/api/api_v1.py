from fastapi import APIRouter

from app.api.routes import auth, users, designs
from app.api.routes.tools import despiece

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(designs.router)
api_router.include_router(despiece.router)
