from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router


app = FastAPI(
    title="AI HeatShield API",
    version="0.1.0",
    description="Hyperlocal Heat Risk & Urban Decision Intelligence Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ai-heatshield.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "project": "AI HeatShield",
        "status": "running",
        "architecture": "fast-first-cache-refresh",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
