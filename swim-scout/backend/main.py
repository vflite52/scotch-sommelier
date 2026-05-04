"""Swim Scout FastAPI backend."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from crew import SwimCrew
from tools.weather import get_location_options


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env or export it.")
    yield


app = FastAPI(
    title="Swim Scout API",
    description="AI crew that evaluates open water swimming conditions.",
    version="1.0.0",
    lifespan=lifespan,
)


class ScoutRequest(BaseModel):
    location: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/locations")
async def list_locations():
    return {"locations": get_location_options()}


@app.post("/scout")
async def scout(request: ScoutRequest):
    location = request.location.strip()
    if not location:
        raise HTTPException(status_code=400, detail="location is required")

    try:
        report = await SwimCrew().evaluate(location)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
