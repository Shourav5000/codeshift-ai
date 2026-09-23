from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.repository import router as repository_router
from app.services.sqs_jobs import start_sqs_worker


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:8080",
    )

    return [
        origin.strip()
        for origin in raw.split(",")
        if origin.strip()
    ]


app = FastAPI(
    title="CodeShift AI",
    description="Agentic Software Intelligence & Modernization Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repository_router)


@app.on_event("startup")
async def startup_event():
    start_sqs_worker()


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
        "status": "healthy",
    }