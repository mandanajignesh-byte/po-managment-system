from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid

import models, schemas

TAX_RATE = 0.05  # 5%

# ─── Vendors ──────────────────────────────────────────────────────────────────

def get_vendors(db: Session):
    return db.query(models.Vendor).order_by(models.Vendor.name).all()

def get_vendor(db: Session, vendor_id: int):
    return db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()

def create_vendor(db: Session, vendor: schemas.VendorCreate):
    db_vendor = models.Vendor(**vendor.dict())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

def update_vendor(db: Session, vendor_id: int, vendor: schemas.VendorCreate):
    db_vendor = get_vendor(db, vendor_id)
    if not db_vendor:
        return None
    for key, value in vendor.dict().items():
        setattr(db_vendor, key, value)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

def delete_vendor(db: Session, vendor_id: int):
    db_vendor = get_vendor(db, vendor_id)
    if not db_vendor:
        return False
    db.delete(db_vendor)
    db.commit()
    return True

# ─── Products ─────────────────────────────────────────────────────────────────

def get_products(db: Session):
    return db.query(models.Product).order_by(models.Product.name).all()

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_product_by_sku(db: Session, sku: str):
    return db.query(models.Product).filter(models.Product.sku == sku).first()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    for key, value in product.dict().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product

# ─── Purchase Orders ──────────────────────────────────────────────────────────

def _generate_ref_no():
    return f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

def calculate_totals(items: list) -> tuple:
    """Returns (subtotal, tax_amount, total_amount)"""
    subtotal = sum(item.line_total for item in items)
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return round(subtotal, 2), tax_amount, total_amount

def get_purchase_orders(db: Session):
    return (
        db.query(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.vendor),
            joinedload(models.PurchaseOrder.line_items).joinedload(models.POLineItem.product),
        )
        .order_by(models.PurchaseOrder.created_at.desc())
        .all()
    )

def get_purchase_order(db: Session, po_id: int):
    return (
        db.query(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.vendor),
            joinedload(models.PurchaseOrder.line_items).joinedload(models.POLineItem.product),
        )
        .filter(models.PurchaseOrder.id == po_id)
        .first()
    )

def create_purchase_order(db: Session, po: schemas.PurchaseOrderCreate):
    # Validate vendor exists
    vendor = get_vendor(db, po.vendor_id)
    if not vendor:
        raise ValueError(f"Vendor with id={po.vendor_id} not found")

    # Build line items & validate products
    line_items = []
    for item in po.items:
        product = get_product(db, item.product_id)
        if not product:
            raise ValueError(f"Product with id={item.product_id} not found")
        line_total = round(product.unit_price * item.quantity, 2)
        line_items.append(
            models.POLineItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=product.unit_price,
                line_total=line_total,
            )
        )

    subtotal, tax_amount, total_amount = calculate_totals(line_items)

    db_po = models.PurchaseOrder(
        reference_no=_generate_ref_no(),
        vendor_id=po.vendor_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=po.notes,
        line_items=line_items,
    )
    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    return get_purchase_order(db, db_po.id)

def update_po_status(db: Session, po_id: int, status: models.POStatus):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == po_id).first()
    if not db_po:
        return None
    db_po.status = status
    db_po.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_po)
    return get_purchase_order(db, po_id)

def delete_purchase_order(db: Session, po_id: int):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == po_id).first()
    if not db_po:
        return False
    db.delete(db_po)
    db.commit()
    return True
