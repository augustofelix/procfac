from fastapi import FastAPI

from app.api import auth

app = FastAPI(title="procfac")
app.include_router(auth.router)
