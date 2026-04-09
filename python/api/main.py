"""
FastAPI entry point for the SpeakRight Sales Analyzer API.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from api.sales_service import sales_router
from api.guest_service import guest_router
from api.attendee_service import attendee_router

app = FastAPI(
    title="SpeakRight Sales Analyzer API",
    description="AI-powered sales call analysis service",
    version="2.0.0",
)

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
wildcard_origins = allowed_origins_str == "*"
allowed_origins = (
    ["*"] if wildcard_origins
    else allowed_origins_str.split(",")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # credentials=True is incompatible with wildcard origins per CORS spec
    allow_credentials=not wildcard_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sales_router, prefix="/sales")
app.include_router(guest_router, prefix="/sales")
app.include_router(attendee_router, prefix="/attendee")


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "SpeakRight Sales Analyzer API"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
