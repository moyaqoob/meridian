from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv
import os

from router.webhook import GITHUB_TOKEN, router as webhook_router

load_dotenv()


print(os.environ.get("GITHUB_TOKEN"))

app = FastAPI()
app.include_router(webhook_router)


uvicorn.run(app,host="localhost",port=8000)



