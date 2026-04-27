"""
FastAPI entry point for the yoursalescoach.ai API.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from api.sales_service import sales_router
from api.guest_service import guest_router
from api.attendee_service import attendee_router
from api.billing_service import billing_router
from api.team_service import team_router
from api.auth import get_current_user
from api.database import SalesDatabaseService
from api.models import AuthInitResponse

_db = SalesDatabaseService()

app = FastAPI(
    title="yoursalescoach.ai API",
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
app.include_router(billing_router, prefix="/billing")
app.include_router(team_router, prefix="/team")


@app.post("/auth/init", response_model=AuthInitResponse, tags=["Auth"])
async def auth_init(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    meta = user.get("user_metadata") or {}
    full_name = meta.get("full_name") or meta.get("name")
    _db.ensure_org(user_id)
    if full_name:
        _db.update_rows(
            table="user_profiles",
            data={"full_name": full_name},
            filters={"id": user_id},
        )
    rows = _db.get_rows(
        table="user_profiles",
        filters={"id": user_id},
        select="org_id, role",
    )
    profile = rows[0] if rows else {}
    return AuthInitResponse(
        org_id=profile.get("org_id", ""),
        role=profile.get("role", "manager"),
    )


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "yoursalescoach.ai API"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
