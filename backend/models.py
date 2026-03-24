from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class POStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELIVERED = "DELIVERED"

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    contact = Column(String(255), nullable=False)
    email = Column(String(255))
    rating = Column(Float, default=3.0)  # 1-5 scale
    created_at = Column(DateTime, default=datetime.utcnow)

    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), default="General")
    unit_price = Column(Float, nullable=False)
    stock_level = Column(Integer, default=0)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    order_items = relationship("POLineItem", back_populates="product")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)      # 5% tax
    total_amount = Column(Float, default=0.0)    # subtotal + tax
    status = Column(Enum(POStatus), default=POStatus.DRAFT)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="purchase_orders")
    line_items = relationship("POLineItem", back_populates="purchase_order", cascade="all, delete-orphan")

class POLineItem(Base):
    __tablename__ = "po_line_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)   # snapshot at order time
    line_total = Column(Float, nullable=False)   # quantity * unit_price

    purchase_order = relationship("PurchaseOrder", back_populates="line_items")
    product = relationship("Product", back_populates="order_items")
