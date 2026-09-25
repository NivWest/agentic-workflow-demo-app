from __future__ import annotations

from fastapi import FastAPI

from src.api.v1.agents import router as agents_router

app = FastAPI(title="Multi-Agent Microservice")
app.include_router(agents_router)
