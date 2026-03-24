# 📦 PO Management System
### IV Innovations Pvt Ltd — Assignment Submission

A full-stack Purchase Order management micro-service with AI-powered product descriptions.

---

## 🗂 Project Structure

```
po_management/
├── backend/
│   ├── main.py          # FastAPI app, all routes
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── crud.py          # DB operations + business logic (tax calc)
│   ├── database.py      # SQLAlchemy engine setup
│   └── requirements.txt
├── frontend/
│   └── po_management.jsx  # React SPA (single file, deployable)
├── schema.sql           # PostgreSQL schema + seed data
└── README.md
```

---

## ⚙️ Setup & Running

### 1. PostgreSQL

```bash
# Create DB
createdb po_management

# Run schema
psql -U postgres -d po_management -f schema.sql
```

### 2. Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt

# Configure DB connection (optional, defaults to localhost)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/po_management"

# Run
uvicorn main:app --reload --port 8000
```

API docs auto-available at: `http://localhost:8000/docs`

### 3. Frontend

The `po_management.jsx` is a standalone React component. To run it:

```bash
# Option A: Paste into https://claude.ai as an artifact (instant demo)

# Option B: Vite project
npm create vite@latest frontend -- --template react
cd frontend
npm install
# Replace src/App.jsx with po_management.jsx content
npm run dev
```

**Demo credentials:** Any email + password `demo123`

The frontend auto-falls back to mock data if the backend is not running — ideal for demo.

---

## 🗄 Database Design

### Why this schema?

```
vendors ──< purchase_orders ──< po_line_items >── products
```

| Decision | Rationale |
|---|---|
| `po_line_items.unit_price` | Snapshot of price at order time — prevents price drift corrupting historical POs |
| `subtotal / tax_amount / total_amount` split | Explicit fields make reporting and auditing trivial without recalculation |
| `postatus` ENUM | DB-enforced state machine prevents invalid status strings |
| `ON DELETE CASCADE` on line_items | Deleting a PO cleans up orphaned line items automatically |
| `ON DELETE RESTRICT` on vendor/product FK | Prevents accidental deletion of a vendor who has live POs |

### Tax Calculation Logic (in `crud.py`)

```python
TAX_RATE = 0.05

def calculate_totals(items):
    subtotal    = sum(item.line_total for item in items)
    tax_amount  = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total_amount
```

This runs server-side at PO creation — the frontend shows a live preview but the authoritative calculation always happens in the backend.

---

## 🔐 Authentication

- JWT-based auth via `/auth/login`
- Token stored in memory (not localStorage) for security
- In production: swap `handleLogin` to redirect to Google/Microsoft OAuth; the `/auth/login` endpoint validates the returned OAuth token via Google's userinfo endpoint and issues your own JWT
- All API routes require `Authorization: Bearer <token>` header

---

## ✨ Gen AI Feature

- **"Auto-Description" button** appears next to each product row in the Create PO form
- Calls Claude API (`claude-sonnet-4-20250514`) with the product name + category
- Generates a professional 2-sentence B2B marketing description
- Falls back gracefully if the API is unavailable

---

## 🚀 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Get JWT token |
| GET | `/vendors` | List all vendors |
| POST | `/vendors` | Create vendor |
| GET | `/products` | List all products |
| POST | `/products` | Create product |
| GET | `/purchase-orders` | List all POs |
| POST | `/purchase-orders` | Create PO (auto-calculates tax) |
| GET | `/purchase-orders/{id}` | Get PO with line items |
| PATCH | `/purchase-orders/{id}/status` | Update PO status |
| DELETE | `/purchase-orders/{id}` | Delete PO |

---

## 🏆 Bonus Features

| Bonus Item | Status |
|---|---|
| AI Auto-Description (Gemini/Claude) | ✅ Implemented via Claude API |
| NoSQL for AI logs | 📌 Add MongoDB logger in `crud.py` `handleAutoDesc` — log `{product_id, name, description, timestamp}` |
| Node.js real-time notifications | 📌 Add Socket.IO server; call `io.emit('po_status_changed', {id, status})` in `update_po_status()` |
| Spring Boot Vendor microservice | 📌 Extract `/vendors` routes into a Spring Boot app; point frontend `BASE_URL` for `/vendors` to port 8081 |

---

## 🎨 Frontend Features

- **Dashboard** with stats cards (total POs, pending, approved, total value)
- **Filter by status** + search by PO# or vendor name
- **Dynamic "Add Row"** — add/remove product rows before submitting, live subtotal/tax/total preview
- **Inline status actions** — approve/reject directly from table
- **PO Detail modal** — full breakdown with line items
- **✨ AI Auto-Description** per product row
- **Demo mode** — works without backend using mock data

---

*Built by: [Your Name] | Stack: FastAPI + PostgreSQL + React + Claude API*
