"""
AI Services Module
──────────────────
1. PO Anomaly Detection  — flags suspicious orders before creation
2. Vendor Recommender    — ranks vendors by category using order history
3. Auto-Description      — 2-sentence B2B marketing copy for products

All results are logged to MongoDB (async, non-blocking).
"""

import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient

# ─── Config ───────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = "po_ai_logs"

_mongo_client: Optional[AsyncIOMotorClient] = None

def get_mongo():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGO_URL)
    return _mongo_client[MONGO_DB]

# ─── Core Claude caller ───────────────────────────────────────────────────────

async def _call_claude(prompt: str, system: str = "", max_tokens: int = 500) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["content"][0]["text"]

async def _log_to_mongo(collection: str, data: dict):
    """Fire-and-forget MongoDB logging — never blocks the main request."""
    try:
        db = get_mongo()
        await db[collection].insert_one({**data, "logged_at": datetime.utcnow()})
    except Exception:
        pass  # Logging must never crash the main flow

# ─── 1. PO Anomaly Detection ──────────────────────────────────────────────────

ANOMALY_SYSTEM = """You are an ERP risk analyst for a B2B procurement system.
Analyse the purchase order and flag genuine anomalies only.
Respond ONLY with a valid JSON object — no markdown, no explanation outside JSON.
Schema:
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "anomalies": [{"type": str, "message": str, "severity": "info"|"warning"|"critical"}],
  "recommendation": str
}"""

async def detect_anomalies(po_data: dict, vendor: dict, items: list) -> dict:
    """
    Analyses a PO before creation and returns risk assessment.
    po_data  : {vendor_id, notes, total_estimated}
    vendor   : {name, rating, total_past_orders}
    items    : [{product_name, category, quantity, unit_price, stock_level}]
    """
    prompt = f"""
Analyse this Purchase Order for anomalies:

VENDOR:
- Name: {vendor.get('name')}
- Rating: {vendor.get('rating')}/5
- Past POs with this vendor: {vendor.get('past_pos', 0)}

ORDER ITEMS:
{json.dumps(items, indent=2)}

TOTALS:
- Estimated total (before tax): ₹{po_data.get('subtotal', 0):,.2f}
- Number of line items: {len(items)}

Flag issues like: unusually large quantities vs stock, low-rated vendor for high-value order,
single vendor dependency for critical items, price spikes vs historical, duplicate products.
"""
    try:
        raw = await _call_claude(prompt, system=ANOMALY_SYSTEM, max_tokens=600)
        result = json.loads(raw)
    except Exception:
        result = {"risk_level": "LOW", "anomalies": [], "recommendation": "Analysis unavailable."}

    # Log to MongoDB
    asyncio.create_task(_log_to_mongo("anomaly_logs", {
        "vendor": vendor.get("name"),
        "items_count": len(items),
        "subtotal": po_data.get("subtotal", 0),
        "result": result,
    }))

    return result

# ─── 2. Vendor Recommender ────────────────────────────────────────────────────

VENDOR_SYSTEM = """You are a procurement intelligence engine.
Rank the given vendors for a specific purchase category using past performance data.
Respond ONLY with a valid JSON array — no markdown, no text outside JSON.
Schema: [{"vendor_id": int, "vendor_name": str, "score": float, "reason": str}]
Sorted best-first. Score is 0-100."""

async def recommend_vendors(category: str, vendors: list, order_history: list) -> list:
    """
    Ranks vendors for a given product category.
    vendors       : [{id, name, rating, email}]
    order_history : [{vendor_name, category, total_amount, status}]
    """
    prompt = f"""
Recommend the best vendors for purchasing: {category}

AVAILABLE VENDORS:
{json.dumps(vendors, indent=2)}

RECENT ORDER HISTORY (last 20 POs):
{json.dumps(order_history[-20:], indent=2)}

Score each vendor 0-100 based on: rating, delivery success rate (DELIVERED status),
total spend (reliability signal), and suitability for the category.
"""
    try:
        raw = await _call_claude(prompt, system=VENDOR_SYSTEM, max_tokens=600)
        result = json.loads(raw)
    except Exception:
        # Fallback: sort by rating
        result = [{"vendor_id": v["id"], "vendor_name": v["name"],
                   "score": v.get("rating", 3) * 20, "reason": "Based on vendor rating."} for v in vendors]

    asyncio.create_task(_log_to_mongo("recommendation_logs", {
        "category": category,
        "vendors_evaluated": len(vendors),
        "top_pick": result[0] if result else None,
    }))

    return result

# ─── 3. Auto-Description ──────────────────────────────────────────────────────

async def generate_description(product_name: str, category: str, user_email: str = "") -> str:
    """Generates a 2-sentence B2B marketing description for a product."""
    prompt = (
        f'Write a professional 2-sentence B2B marketing description for a procurement product '
        f'named "{product_name}" in the "{category}" category. '
        f'Be concise, persuasive, and technical. Return only the description.'
    )
    try:
        description = await _call_claude(prompt, max_tokens=150)
    except Exception:
        description = f"{product_name} is a high-quality {category} product designed for enterprise use."

    asyncio.create_task(_log_to_mongo("description_logs", {
        "product_name": product_name,
        "category": category,
        "description": description,
        "requested_by": user_email,
    }))

    return description

# ─── 4. MongoDB log retrieval ─────────────────────────────────────────────────

async def get_ai_logs(collection: str, limit: int = 50) -> list:
    db = get_mongo()
    cursor = db[collection].find({}, {"_id": 0}).sort("logged_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
