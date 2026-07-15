from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_db
from routers.auth import router as auth_router
from routers.prs import router as prs_router
from routers.repos import router as repos_router
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
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(prs_router)
app.include_router(webhook_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
