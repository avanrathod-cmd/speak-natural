"""
Sales analyzer API endpoints.

Routes (mounted at /sales in main.py):
    POST /products          — create product + auto-generate script
    GET  /products          — list org products
    GET  /scripts/{id}      — get script detail
    POST /scripts/generate  — regenerate script for a product
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import get_current_user
from api.database import SalesDatabaseService
from api.models import (
    ProductCreateRequest,
    ProductResponse,
    RegenerateScriptRequest,
    ScriptResponse,
)
from services.script_generator import ScriptGeneratorService

sales_router = APIRouter(tags=["Sales"])

_db = SalesDatabaseService()
_script_gen = ScriptGeneratorService()


@sales_router.post("/products", response_model=ProductResponse)
async def create_product(
    req: ProductCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a product and auto-generate a sales script for it."""
    user_id = user["user_id"]

    product = _db.create_product(
        user_id=user_id,
        name=req.name,
        description=req.description,
        customer_profile=req.customer_profile,
        talking_points=req.talking_points,
    )

    script_data = _script_gen.generate_script(
        name=req.name,
        description=req.description or "",
        customer_profile=req.customer_profile or "",
        talking_points=req.talking_points or "",
    )

    script = _db.create_sales_script(
        user_id=user_id,
        product_id=product["id"],
        org_id=product["org_id"],
        title=f"{req.name} — Sales Script",
        script_data=script_data,
    )

    return ProductResponse(
        id=product["id"],
        name=product["name"],
        description=product.get("description"),
        customer_profile=product.get("customer_profile"),
        talking_points=product.get("talking_points"),
        script_id=script["id"],
        created_at=product.get("created_at"),
    )


@sales_router.get(
    "/products", response_model=list[ProductResponse]
)
async def list_products(
    user: dict = Depends(get_current_user),
    search: Optional[str] = Query(
        None, description="Filter across name, description, "
        "customer_profile, and talking_points"
    ),
    order_by: str = Query(
        "created_at", description="Column to sort by"
    ),
    order_desc: bool = Query(
        True, description="Sort descending if true"
    ),
):
    """List all products visible to the authenticated user's org."""
    products = _db.list_products(
        user_id=user["user_id"],
        search=search,
        order_by=order_by,
        order_desc=order_desc,
    )

    result = []
    for p in products:
        script = _db.get_latest_sales_script_for_product(p["id"])
        result.append(ProductResponse(
            id=p["id"],
            name=p["name"],
            description=p.get("description"),
            customer_profile=p.get("customer_profile"),
            talking_points=p.get("talking_points"),
            script_id=script["id"] if script else None,
            created_at=p.get("created_at"),
        ))

    return result


@sales_router.get(
    "/scripts/{script_id}", response_model=ScriptResponse
)
async def get_script(
    script_id: str,
    user: dict = Depends(get_current_user),
):
    """Fetch a sales script by ID."""
    row = _db.get_sales_script(script_id)
    if not row:
        raise HTTPException(
            status_code=404, detail="Script not found"
        )
    return _format_script(row)


@sales_router.post(
    "/scripts/regenerate", response_model=ScriptResponse
)
async def regenerate_script(
    req: RegenerateScriptRequest,
    user: dict = Depends(get_current_user),
):
    """Regenerate a sales script for an existing product."""
    user_id = user["user_id"]

    products = _db.list_products(user_id)
    product = next(
        (p for p in products if p["id"] == req.product_id), None
    )
    if not product:
        raise HTTPException(
            status_code=404, detail="Product not found"
        )

    script_data = _script_gen.generate_script(
        name=product["name"],
        description=product.get("description") or "",
        customer_profile=product.get("customer_profile") or "",
        talking_points=product.get("talking_points") or "",
    )

    title = f"{product['name']} — Sales Script"
    existing = _db.get_latest_sales_script_for_product(
        product["id"]
    )

    if existing:
        script = _db.update_sales_script(
            script_id=existing["id"],
            title=title,
            script_data=script_data,
        )
    else:
        script = _db.create_sales_script(
            user_id=user_id,
            product_id=product["id"],
            org_id=product["org_id"],
            title=title,
            script_data=script_data,
        )

    return _format_script(script)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _format_script(row: dict) -> ScriptResponse:
    """Parse a sales_scripts DB row into a ScriptResponse."""
    content = json.loads(row["script_content"])
    return ScriptResponse(
        id=row["id"],
        product_id=row.get("product_id"),
        title=row["title"],
        opening=content.get("opening", ""),
        discovery_questions=content.get(
            "discovery_questions", []
        ),
        value_propositions=content.get("value_propositions", []),
        objection_handlers=content.get("objection_handlers", {}),
        closing=content.get("closing", ""),
        key_phrases=content.get("key_phrases", []),
        created_at=row.get("created_at"),
    )
