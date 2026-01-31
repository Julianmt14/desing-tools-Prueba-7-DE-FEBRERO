from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1 import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="1.0.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/")
    async def root():
        return {"message": "API Design Tools", "version": "1.0.0"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_application()
