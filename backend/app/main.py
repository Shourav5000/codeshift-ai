from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.repository import router as repository_router


app = FastAPI(
    title="CodeShift AI",
    description="Agentic Software Intelligence & Modernization Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repository_router)


@app.get("/")
async def root():
    return {
        "application": "CodeShift AI",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }