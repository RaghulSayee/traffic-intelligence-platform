from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import engine


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage resources used during the application's lifetime."""

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=("Backend API for the intelligent traffic-violation platform."),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(settings.parsed_cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)
