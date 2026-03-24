from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import POStatus

# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

# ─── Vendor ───────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    contact: str = Field(..., min_length=2)
    email: Optional[str] = None
    rating: float = Field(default=3.0, ge=1.0, le=5.0)

class Vendor(VendorCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ─── Product ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    sku: str = Field(..., min_length=2, max_length=100)
    category: str = Field(default="General", max_length=100)
    unit_price: float = Field(..., gt=0)
    stock_level: int = Field(default=0, ge=0)
    description: Optional[str] = None

class Product(ProductCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ─── PO Line Items ────────────────────────────────────────────────────────────

class POLineItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class POLineItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float
    product: Optional[Product] = None

    class Config:
        from_attributes = True

# ─── Purchase Orders ──────────────────────────────────────────────────────────

class PurchaseOrderCreate(BaseModel):
    vendor_id: int
    notes: Optional[str] = None
    items: List[POLineItemCreate] = Field(..., min_items=1)

class StatusUpdate(BaseModel):
    status: POStatus

class PurchaseOrderOut(BaseModel):
    id: int
    reference_no: str
    vendor_id: int
    subtotal: float
    tax_amount: float
    total_amount: float
    status: POStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    vendor: Optional[Vendor] = None
    line_items: List[POLineItemOut] = []

    class Config:
        from_attributes = True

# ─── AI Request Schemas ───────────────────────────────────────────────────────

class AnomalyCheckRequest(BaseModel):
    vendor_id: int
    items: List[POLineItemCreate]

class AutoDescRequest(BaseModel):
    product_name: str
    category: str = "General"
