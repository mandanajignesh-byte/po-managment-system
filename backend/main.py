from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import jwt, datetime, json, io

from database import get_db, engine
import models, schemas, crud
from ai_services import detect_anomalies, recommend_vendors, generate_description, get_ai_logs
from websocket_manager import manager, notify_po_created, notify_status_changed, notify_anomaly_detected
from audit_pdf import write_audit, get_audit_logs, generate_po_pdf, AuditLog

models.Base.metadata.create_all(bind=engine)
AuditLog.metadata.create_all(bind=engine)

app = FastAPI(title="PO Management System — IV Innovations", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM  = "HS256"
security   = HTTPBearer(auto_error=False)

# ─── Auth ─────────────────────────────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.LoginRequest):
    if credentials.email and credentials.password == "demo123":
        token = jwt.encode(
            {
                "sub": credentials.email,
                "name": credentials.email.split("@")[0].title(),
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
            },
            SECRET_KEY, algorithm=ALGORITHM,
        )
        return {"access_token": token, "token_type": "bearer", "user": {"email": credentials.email}}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user

# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{user_email}")
async def websocket_endpoint(websocket: WebSocket, user_email: str):
    await manager.connect(websocket, user_email)
    try:
        await websocket.send_text(json.dumps({
            "type": "CONNECTED",
            "message": f"Real-time notifications active. {manager.connected_count} user(s) online.",
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_email)

@app.get("/ws/status")
def ws_status():
    return {"connected_users": manager.connected_count}

# ─── Vendors ──────────────────────────────────────────────────────────────────

@app.get("/vendors", response_model=List[schemas.Vendor])
def list_vendors(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return crud.get_vendors(db)

@app.post("/vendors", response_model=schemas.Vendor, status_code=201)
def create_vendor(vendor: schemas.VendorCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    v = crud.create_vendor(db, vendor)
    write_audit(db, "Vendor", v.id, "CREATED", new_value=vendor.model_dump_json(), performed_by=user.get("sub",""))
    return v

@app.get("/vendors/{vendor_id}", response_model=schemas.Vendor)
def get_vendor(vendor_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    v = crud.get_vendor(db, vendor_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return v

@app.put("/vendors/{vendor_id}", response_model=schemas.Vendor)
def update_vendor(vendor_id: int, vendor: schemas.VendorCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    old = crud.get_vendor(db, vendor_id)
    if not old:
        raise HTTPException(status_code=404, detail="Vendor not found")
    updated = crud.update_vendor(db, vendor_id, vendor)
    write_audit(db, "Vendor", vendor_id, "UPDATED", old_value=old.name, new_value=vendor.model_dump_json(), performed_by=user.get("sub",""))
    return updated

@app.delete("/vendors/{vendor_id}", status_code=204)
def delete_vendor(vendor_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not crud.delete_vendor(db, vendor_id):
        raise HTTPException(status_code=404, detail="Vendor not found")
    write_audit(db, "Vendor", vendor_id, "DELETED", performed_by=user.get("sub",""))

# ─── Products ─────────────────────────────────────────────────────────────────

@app.get("/products", response_model=List[schemas.Product])
def list_products(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return crud.get_products(db)

@app.post("/products", response_model=schemas.Product, status_code=201)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if crud.get_product_by_sku(db, product.sku):
        raise HTTPException(status_code=400, detail=f"SKU '{product.sku}' already exists")
    p = crud.create_product(db, product)
    write_audit(db, "Product", p.id, "CREATED", new_value=product.model_dump_json(), performed_by=user.get("sub",""))
    return p

@app.get("/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = crud.get_product(db, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    updated = crud.update_product(db, product_id, product)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    write_audit(db, "Product", product_id, "UPDATED", new_value=product.model_dump_json(), performed_by=user.get("sub",""))
    return updated

# ─── Purchase Orders ──────────────────────────────────────────────────────────

@app.get("/purchase-orders", response_model=List[schemas.PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return crud.get_purchase_orders(db)

@app.post("/purchase-orders", response_model=schemas.PurchaseOrderOut, status_code=201)
async def create_purchase_order(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        db_po = crud.create_purchase_order(db, po)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    write_audit(db, "PurchaseOrder", db_po.id, "CREATED",
                new_value=json.dumps({"ref": db_po.reference_no, "total": db_po.total_amount}),
                performed_by=user.get("sub",""))

    await notify_po_created({
        "id": db_po.id,
        "reference_no": db_po.reference_no,
        "total_amount": db_po.total_amount,
        "status": db_po.status.value,
        "vendor_name": db_po.vendor.name if db_po.vendor else "",
    })
    return db_po

@app.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrderOut)
def get_purchase_order(po_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    po = crud.get_purchase_order(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return po

@app.patch("/purchase-orders/{po_id}/status", response_model=schemas.PurchaseOrderOut)
async def update_po_status(po_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    old_po = crud.get_purchase_order(db, po_id)
    if not old_po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    old_status = old_po.status.value

    updated = crud.update_po_status(db, po_id, payload.status)

    write_audit(db, "PurchaseOrder", po_id, "STATUS_CHANGED",
                old_value=old_status, new_value=payload.status.value,
                performed_by=user.get("sub",""))

    await notify_status_changed(po_id, updated.reference_no, old_status, payload.status.value, user.get("sub",""))
    return updated

@app.delete("/purchase-orders/{po_id}", status_code=204)
def delete_purchase_order(po_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    po = crud.get_purchase_order(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    write_audit(db, "PurchaseOrder", po_id, "DELETED", old_value=po.reference_no, performed_by=user.get("sub",""))
    crud.delete_purchase_order(db, po_id)

# ─── PDF Export ───────────────────────────────────────────────────────────────

@app.get("/purchase-orders/{po_id}/pdf")
def export_po_pdf(po_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    po = crud.get_purchase_order(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    po_dict = {
        "reference_no": po.reference_no,
        "status": po.status.value,
        "created_at": po.created_at,
        "subtotal": po.subtotal,
        "tax_amount": po.tax_amount,
        "total_amount": po.total_amount,
        "notes": po.notes,
        "vendor": {
            "name": po.vendor.name if po.vendor else "—",
            "contact": po.vendor.contact if po.vendor else "",
            "email": po.vendor.email if po.vendor else "",
            "rating": po.vendor.rating if po.vendor else 0,
        },
        "line_items": [
            {
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "product": {
                    "name": item.product.name if item.product else "—",
                    "sku": item.product.sku if item.product else "—",
                }
            }
            for item in po.line_items
        ]
    }

    pdf_bytes = generate_po_pdf(po_dict)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="PO-{po.reference_no}.pdf"'}
    )

# ─── AI Routes ────────────────────────────────────────────────────────────────

@app.post("/ai/anomaly-check")
async def anomaly_check(payload: schemas.AnomalyCheckRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    vendor = crud.get_vendor(db, payload.vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    items_context = []
    subtotal = 0
    for item in payload.items:
        product = crud.get_product(db, item.product_id)
        if product:
            line_total = product.unit_price * item.quantity
            subtotal += line_total
            items_context.append({
                "product_name": product.name,
                "category": product.category,
                "quantity": item.quantity,
                "unit_price": product.unit_price,
                "stock_level": product.stock_level,
                "line_total": line_total,
            })

    all_pos = crud.get_purchase_orders(db)
    past_pos = [p for p in all_pos if p.vendor_id == payload.vendor_id]

    result = await detect_anomalies(
        po_data={"subtotal": subtotal},
        vendor={"name": vendor.name, "rating": vendor.rating, "past_pos": len(past_pos)},
        items=items_context,
    )

    if result.get("risk_level") in ("MEDIUM", "HIGH"):
        await notify_anomaly_detected(f"DRAFT-{payload.vendor_id}", result["risk_level"], result.get("anomalies", []))

    return result

@app.get("/ai/vendor-recommendation")
async def vendor_recommendation(category: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    vendors = crud.get_vendors(db)
    all_pos = crud.get_purchase_orders(db)
    order_history = [
        {"vendor_name": po.vendor.name if po.vendor else "", "category": category,
         "total_amount": po.total_amount, "status": po.status.value}
        for po in all_pos
    ]
    vendors_list = [{"id": v.id, "name": v.name, "rating": v.rating, "email": v.email} for v in vendors]
    result = await recommend_vendors(category, vendors_list, order_history)
    return {"category": category, "recommendations": result}

@app.post("/ai/auto-description")
async def auto_description(payload: schemas.AutoDescRequest, user=Depends(get_current_user)):
    description = await generate_description(payload.product_name, payload.category, user.get("sub",""))
    return {"product_name": payload.product_name, "description": description}

@app.get("/ai/logs/{collection}")
async def ai_logs(collection: str, limit: int = 50, _=Depends(get_current_user)):
    allowed = {"anomaly_logs", "recommendation_logs", "description_logs"}
    if collection not in allowed:
        raise HTTPException(status_code=400, detail=f"Collection must be one of {allowed}")
    logs = await get_ai_logs(collection, limit=limit)
    return {"collection": collection, "count": len(logs), "logs": logs}

# ─── Audit Logs ───────────────────────────────────────────────────────────────

@app.get("/audit-logs")
def audit_logs(entity_type: str = None, entity_id: int = None, limit: int = 100,
               db: Session = Depends(get_db), _=Depends(get_current_user)):
    logs = get_audit_logs(db, entity_type=entity_type, entity_id=entity_id, limit=limit)
    return [{
        "id": l.id, "entity_type": l.entity_type, "entity_id": l.entity_id,
        "action": l.action, "old_value": l.old_value, "new_value": l.new_value,
        "performed_by": l.performed_by, "created_at": l.created_at.isoformat(),
    } for l in logs]

# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok", "version": "2.0.0",
        "features": ["JWT Auth", "AI Anomaly Detection", "AI Vendor Recommender",
                     "WebSocket Notifications", "PDF Export", "Audit Logs", "MongoDB AI Logs"],
        "ws_connections": manager.connected_count,
    }
