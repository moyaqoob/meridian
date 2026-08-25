from contextlib import asynccontextmanager
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_db
from routers.auth import router as auth_router
from routers.health import router as health_router
from routers.prs import router as prs_router
from routers.repos import router as repos_router
from routers.review_stream import router as review_stream_router
from routers.webhook import router as webhook_router

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(prs_router)
app.include_router(review_stream_router)
app.include_router(webhook_router)


if __name__ == "__main__":
    # Reload kills in-process work; ingest/reviews now run in RQ so reload is
    # safer, but still defaults OFF. Set MERIDIAN_RELOAD=1 for hot reload.
    reload = os.environ.get("MERIDIAN_RELOAD", "").lower() in {"1", "true", "yes"}
    uvicorn.run("main:app", host="localhost", port=8000, reload=reload)
