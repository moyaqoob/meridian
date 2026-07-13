from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from core.database import init_db
from routers.auth import router as auth_router
from routers.repos import router as repos_router
from routers.webhook import router as webhook_router

load_dotenv()

app = FastAPI()
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(webhook_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
