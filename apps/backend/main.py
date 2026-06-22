from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from router.webhook import router as webhook_router
from routers.repos import router as repos_router

load_dotenv()

app = FastAPI()
app.include_router(webhook_router)
app.include_router(repos_router)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)



