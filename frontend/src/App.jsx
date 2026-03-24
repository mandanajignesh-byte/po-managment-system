import { useState, useEffect, useCallback, useRef } from "react";

const BASE_URL = "http://localhost:8000";
let authToken = null;

const api = {
  setToken: (t) => { authToken = t; },
  req: async (method, path, body) => {
    const headers = { "Content-Type": "application/json" };
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    const res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(err.detail || "Request failed");
    }
    if (res.status === 204) return null;
    return res.json();
  },
  get: (p) => api.req("GET", p),
  post: (p, b) => api.req("POST", p, b),
  patch: (p, b) => api.req("PATCH", p, b),
  delete: (p) => api.req("DELETE", p),
};

const MOCK = {
  vendors: [
    { id: 1, name: "Tata Supplies Co.", contact: "+91-98765-43210", email: "tata@supplies.in", rating: 4.5 },
    { id: 2, name: "Reliance Procurement", contact: "+91-87654-32109", email: "proc@reliance.in", rating: 4.0 },
    { id: 3, name: "Infosys Tech Parts", contact: "+91-76543-21098", email: "parts@infosys.in", rating: 4.8 },
  ],
  products: [
    { id: 1, name: "Intel Core i9 Processor", sku: "CPU-I9-001", category: "Electronics", unit_price: 45000, stock_level: 50 },
    { id: 2, name: "Samsung 32GB RAM DDR5", sku: "RAM-S32-002", category: "Electronics", unit_price: 12000, stock_level: 200 },
    { id: 3, name: "Western Digital 2TB SSD", sku: "SSD-WD2-003", category: "Storage", unit_price: 8500, stock_level: 150 },
    { id: 4, name: "Logitech MX Keys Keyboard", sku: "KBD-LG-004", category: "Peripherals", unit_price: 9500, stock_level: 75 },
    { id: 5, name: "Dell 27\" 4K Monitor", sku: "MON-DL27-005", category: "Display", unit_price: 35000, stock_level: 30 },
  ],
  pos: [
    { id: 1, reference_no: "PO-20250324-A1B2C3", vendor: { name: "Tata Supplies Co." }, status: "APPROVED", total_amount: 59850, subtotal: 57000, tax_amount: 2850, created_at: "2025-03-20T10:30:00Z", line_items: [{ product: { name: "Intel Core i9 Processor" }, quantity: 1, unit_price: 45000, line_total: 45000 }, { product: { name: "Samsung 32GB RAM DDR5" }, quantity: 1, unit_price: 12000, line_total: 12000 }] },
    { id: 2, reference_no: "PO-20250323-D4E5F6", vendor: { name: "Reliance Procurement" }, status: "PENDING", total_amount: 38325, subtotal: 36500, tax_amount: 1825, created_at: "2025-03-23T14:15:00Z", line_items: [{ product: { name: "Dell 27\" 4K Monitor" }, quantity: 1, unit_price: 35000, line_total: 35000 }] },
    { id: 3, reference_no: "PO-20250322-G7H8I9", vendor: { name: "Infosys Tech Parts" }, status: "DRAFT", total_amount: 9975, subtotal: 9500, tax_amount: 475, created_at: "2025-03-22T09:00:00Z", line_items: [{ product: { name: "Logitech MX Keys Keyboard" }, quantity: 1, unit_price: 9500, line_total: 9500 }] },
  ],
};

const STATUS_CONFIG = {
  DRAFT: { color: "#94a3b8", bg: "rgba(148,163,184,0.12)", label: "Draft" },
  PENDING: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", label: "Pending" },
  APPROVED: { color: "#10b981", bg: "rgba(16,185,129,0.12)", label: "Approved" },
  REJECTED: { color: "#ef4444", bg: "rgba(239,68,68,0.12)", label: "Rejected" },
  DELIVERED: { color: "#6366f1", bg: "rgba(99,102,241,0.12)", label: "Delivered" },
};

const fmt = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
const fmtDate = (d) => new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });

async function generateDescription(productName, category) {
  const res = await fetch(`${BASE_URL}/ai/auto-description`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${authToken}`
    },
    body: JSON.stringify({ product_name: productName, category })
  });
  const data = await res.json();
  return data.description || "Description unavailable.";
}
    

function StarRating({ rating }) {
  return (
    <span style={{ color: "#f59e0b", fontSize: 13, letterSpacing: 1 }}>
      {"★".repeat(Math.floor(rating))}{"☆".repeat(5 - Math.floor(rating))}
      <span style={{ color: "#94a3b8", marginLeft: 4, fontSize: 11 }}>{rating}</span>
    </span>
  );
}

function Badge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.DRAFT;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33`, letterSpacing: "0.05em", textTransform: "uppercase" }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: cfg.color }} />
      {cfg.label}
    </span>
  );
}

function Spinner() {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: 40 }}>
      <div style={{ width: 32, height: 32, borderRadius: "50%", border: "3px solid rgba(99,102,241,0.2)", borderTopColor: "#6366f1", animation: "spin 0.8s linear infinite" }} />
    </div>
  );
}

function Toast({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  const colors = { success: "#10b981", error: "#ef4444", info: "#6366f1" };
  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, background: "#1e293b", border: `1px solid ${colors[type]}44`, borderLeft: `4px solid ${colors[type]}`, borderRadius: 10, padding: "14px 20px", color: "#f1f5f9", fontSize: 14, fontWeight: 500, boxShadow: "0 8px 32px rgba(0,0,0,0.4)", maxWidth: 380, animation: "slideUp 0.3s ease" }}>
      {msg}
    </div>
  );
}

function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState("admin@ivinnovations.in");
  const [pass, setPass] = useState("demo123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      let token, user;
      try {
        const res = await api.post("/auth/login", { email, password: pass });
        token = res.access_token; user = res.user;
      } catch {
        if (pass === "demo123") { token = "demo-token-" + Date.now(); user = { email, name: email.split("@")[0] }; }
        else throw new Error("Invalid credentials. Use password: demo123");
      }
      api.setToken(token);
      onLogin({ token, user });
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)", fontFamily: "'Sora', 'DM Sans', sans-serif" }}>
      <div style={{ background: "rgba(15,23,42,0.9)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 20, padding: "48px 40px", width: "100%", maxWidth: 420, boxShadow: "0 25px 80px rgba(99,102,241,0.2)", backdropFilter: "blur(20px)" }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px", fontSize: 24, boxShadow: "0 8px 24px rgba(99,102,241,0.4)" }}>📦</div>
          <h1 style={{ color: "#f1f5f9", fontSize: 22, fontWeight: 700, margin: 0 }}>PO Management</h1>
          <p style={{ color: "#64748b", fontSize: 13, margin: "6px 0 0" }}>IV Innovations Pvt Ltd</p>
        </div>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", color: "#94a3b8", fontSize: 12, fontWeight: 600, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Email</label>
            <input value={email} onChange={e => setEmail(e.target.value)} type="email" required style={{ width: "100%", padding: "12px 14px", background: "rgba(30,41,59,0.8)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 10, color: "#f1f5f9", fontSize: 14, outline: "none", boxSizing: "border-box" }} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ display: "block", color: "#94a3b8", fontSize: 12, fontWeight: 600, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Password</label>
            <input value={pass} onChange={e => setPass(e.target.value)} type="password" required style={{ width: "100%", padding: "12px 14px", background: "rgba(30,41,59,0.8)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 10, color: "#f1f5f9", fontSize: 14, outline: "none", boxSizing: "border-box" }} />
          </div>
          <p style={{ color: "#475569", fontSize: 11, marginBottom: 20 }}>Demo credentials: any email + password <code style={{ color: "#6366f1" }}>demo123</code></p>
          {error && <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, padding: "10px 14px", color: "#f87171", fontSize: 13, marginBottom: 16 }}>{error}</div>}
          <button type="submit" disabled={loading} style={{ width: "100%", padding: "13px", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", border: "none", borderRadius: 10, color: "white", fontSize: 15, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, boxShadow: "0 4px 16px rgba(99,102,241,0.4)" }}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Dashboard({ pos, onCreateNew, onViewPO, onUpdateStatus, loading }) {
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const filtered = pos.filter(po => {
    const matchStatus = filter === "ALL" || po.status === filter;
    const matchSearch = !search || po.reference_no.toLowerCase().includes(search.toLowerCase()) || po.vendor?.name?.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });
  const stats = { total: pos.length, pending: pos.filter(p => p.status === "PENDING").length, approved: pos.filter(p => p.status === "APPROVED").length, totalValue: pos.reduce((s, p) => s + p.total_amount, 0) };
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        {[{ label: "Total POs", value: stats.total, icon: "📋", color: "#6366f1" }, { label: "Pending Review", value: stats.pending, icon: "⏳", color: "#f59e0b" }, { label: "Approved", value: stats.approved, icon: "✅", color: "#10b981" }, { label: "Total Value", value: fmt(stats.totalValue), icon: "💰", color: "#8b5cf6", small: true }].map(s => (
          <div key={s.label} style={{ background: "rgba(15,23,42,0.6)", border: "1px solid rgba(99,102,241,0.15)", borderRadius: 14, padding: "20px 22px", borderTop: `3px solid ${s.color}` }}>
            <div style={{ fontSize: 22, marginBottom: 8 }}>{s.icon}</div>
            <div style={{ fontSize: s.small ? 18 : 28, fontWeight: 700, color: "#f1f5f9", lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4, fontWeight: 500 }}>{s.label}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 20, flexWrap: "wrap" }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by PO# or vendor..." style={{ flex: 1, minWidth: 200, padding: "10px 14px", background: "rgba(30,41,59,0.8)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 10, color: "#f1f5f9", fontSize: 13, outline: "none" }} />
        <div style={{ display: "flex", gap: 6 }}>
          {["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED", "DELIVERED"].map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid", borderColor: filter === s ? "#6366f1" : "rgba(99,102,241,0.2)", background: filter === s ? "rgba(99,102,241,0.2)" : "transparent", color: filter === s ? "#818cf8" : "#64748b", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>{s === "ALL" ? "All" : STATUS_CONFIG[s]?.label}</button>
          ))}
        </div>
        <button onClick={onCreateNew} style={{ padding: "10px 20px", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", border: "none", borderRadius: 10, color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, boxShadow: "0 4px 14px rgba(99,102,241,0.35)", whiteSpace: "nowrap" }}>
          <span style={{ fontSize: 16 }}>+</span> New PO
        </button>
      </div>
      {loading ? <Spinner /> : (
        <div style={{ background: "rgba(15,23,42,0.6)", border: "1px solid rgba(99,102,241,0.15)", borderRadius: 14, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(99,102,241,0.15)" }}>
                {["Reference No.", "Vendor", "Items", "Subtotal", "Tax (5%)", "Total", "Status", "Date", "Actions"].map(h => (
                  <th key={h} style={{ padding: "14px 16px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "#64748b", letterSpacing: "0.08em", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={9} style={{ padding: 40, textAlign: "center", color: "#475569", fontSize: 14 }}>No purchase orders found</td></tr>
              ) : filtered.map((po, i) => (
                <tr key={po.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid rgba(99,102,241,0.08)" : "none" }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(99,102,241,0.04)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <td style={{ padding: "14px 16px" }}><span style={{ fontFamily: "monospace", fontSize: 12, color: "#818cf8", fontWeight: 600 }}>{po.reference_no}</span></td>
                  <td style={{ padding: "14px 16px", color: "#e2e8f0", fontSize: 13, fontWeight: 500 }}>{po.vendor?.name}</td>
                  <td style={{ padding: "14px 16px", color: "#94a3b8", fontSize: 13 }}>{po.line_items?.length || 0} item{po.line_items?.length !== 1 ? "s" : ""}</td>
                  <td style={{ padding: "14px 16px", color: "#94a3b8", fontSize: 13 }}>{fmt(po.subtotal)}</td>
                  <td style={{ padding: "14px 16px", color: "#f59e0b", fontSize: 13 }}>{fmt(po.tax_amount)}</td>
                  <td style={{ padding: "14px 16px", color: "#f1f5f9", fontSize: 14, fontWeight: 700 }}>{fmt(po.total_amount)}</td>
                  <td style={{ padding: "14px 16px" }}><Badge status={po.status} /></td>
                  <td style={{ padding: "14px 16px", color: "#64748b", fontSize: 12 }}>{fmtDate(po.created_at)}</td>
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      
                        <button onClick={() => onViewPO(po)} style={{ padding: "5px 12px", background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 6, color: "#818cf8", fontSize: 12, cursor: "pointer", fontWeight: 500 }}>View</button>
                        <select onChange={e => { if (e.target.value) onUpdateStatus(po.id, e.target.value); e.target.value = ""; }}
                          style={{ padding: "5px 8px", background: "rgba(30,41,59,0.9)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 6, color: "#94a3b8", fontSize: 11, cursor: "pointer" }}>
                          <option value="">Change...</option>
                          <option value="PENDING">Pending</option>
                          <option value="APPROVED">Approved</option>
                          <option value="REJECTED">Rejected</option>
                          <option value="DELIVERED">Delivered</option>
                          <option value="DRAFT">Draft</option>
                        </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PODetailModal({ po, onClose }) {
  if (!po) return null;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)", padding: 20 }} onClick={onClose}>
      <div style={{ background: "#0f172a", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 18, padding: 32, width: "100%", maxWidth: 640, maxHeight: "80vh", overflowY: "auto", boxShadow: "0 25px 80px rgba(0,0,0,0.6)" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <h2 style={{ color: "#f1f5f9", fontSize: 18, fontWeight: 700, margin: 0 }}>{po.reference_no}</h2>
            <p style={{ color: "#64748b", fontSize: 12, margin: "4px 0 0" }}>Created {fmtDate(po.created_at)}</p>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Badge status={po.status} />
            <button onClick={() => window.open(`http://localhost:8000/purchase-orders/${po.id}/pdf`, '_blank')}
              style={{ padding: "6px 14px", background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: 7, color: "#10b981", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
              📄 Export PDF
            </button>
            <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748b", fontSize: 20, cursor: "pointer" }}>×</button>          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
          <div style={{ background: "rgba(30,41,59,0.6)", borderRadius: 10, padding: 14 }}>
            <div style={{ color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Vendor</div>
            <div style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600 }}>{po.vendor?.name}</div>
            <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 2 }}>{po.vendor?.contact}</div>
            {po.vendor?.rating && <div style={{ marginTop: 6 }}><StarRating rating={po.vendor.rating} /></div>}
          </div>
          <div style={{ background: "rgba(30,41,59,0.6)", borderRadius: 10, padding: 14 }}>
            <div style={{ color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Amount Breakdown</div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#94a3b8", marginBottom: 4 }}><span>Subtotal</span><span>{fmt(po.subtotal)}</span></div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#f59e0b", marginBottom: 6 }}><span>GST/Tax (5%)</span><span>+ {fmt(po.tax_amount)}</span></div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 15, color: "#f1f5f9", fontWeight: 700, borderTop: "1px solid rgba(99,102,241,0.2)", paddingTop: 6 }}><span>Total</span><span>{fmt(po.total_amount)}</span></div>
          </div>
        </div>
        <div style={{ color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>Line Items</div>
        <div style={{ background: "rgba(30,41,59,0.4)", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ borderBottom: "1px solid rgba(99,102,241,0.15)" }}>{["Product", "Qty", "Unit Price", "Total"].map(h => <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, color: "#64748b", fontWeight: 600 }}>{h}</th>)}</tr></thead>
            <tbody>{po.line_items?.map((item, i) => <tr key={i} style={{ borderBottom: i < po.line_items.length - 1 ? "1px solid rgba(99,102,241,0.08)" : "none" }}><td style={{ padding: "10px 14px", color: "#e2e8f0", fontSize: 13 }}>{item.product?.name}</td><td style={{ padding: "10px 14px", color: "#94a3b8", fontSize: 13 }}>{item.quantity}</td><td style={{ padding: "10px 14px", color: "#94a3b8", fontSize: 13 }}>{fmt(item.unit_price)}</td><td style={{ padding: "10px 14px", color: "#f1f5f9", fontSize: 13, fontWeight: 600 }}>{fmt(item.line_total)}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CreatePOForm({ vendors, products, onSubmit, onCancel }) {
  const [vendorId, setVendorId] = useState("");
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState([{ id: Date.now(), product_id: "", quantity: 1 }]);
  const [aiDesc, setAiDesc] = useState({});
  const [aiLoading, setAiLoading] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const addRow = () => setRows(r => [...r, { id: Date.now(), product_id: "", quantity: 1 }]);
  const removeRow = (id) => setRows(r => r.filter(row => row.id !== id));
  const updateRow = (id, field, val) => setRows(r => r.map(row => row.id === id ? { ...row, [field]: val } : row));
  const getProduct = (pid) => products.find(p => p.id === parseInt(pid));
  const calcSubtotal = () => rows.reduce((s, r) => { const p = getProduct(r.product_id); return s + (p ? p.unit_price * r.quantity : 0); }, 0);
  const subtotal = calcSubtotal();
  const tax = subtotal * 0.05;
  const total = subtotal + tax;

  const handleAutoDesc = async (rowId, productId) => {
    const product = getProduct(productId);
    if (!product) return;
    setAiLoading(l => ({ ...l, [rowId]: true }));
    try {
      const desc = await generateDescription(product.name, product.category);
      setAiDesc(d => ({ ...d, [rowId]: desc }));
    } catch { setAiDesc(d => ({ ...d, [rowId]: "AI description unavailable." })); }
    finally { setAiLoading(l => ({ ...l, [rowId]: false })); }
  };

  const handleSubmit = async () => {
    if (!vendorId) return alert("Please select a vendor");
    const validRows = rows.filter(r => r.product_id && r.quantity > 0);
    if (validRows.length === 0) return alert("Add at least one product");
    setSubmitting(true);
    try { await onSubmit({ vendor_id: parseInt(vendorId), notes, items: validRows.map(r => ({ product_id: parseInt(r.product_id), quantity: parseInt(r.quantity) })) }); }
    finally { setSubmitting(false); }
  };

  const inputStyle = { background: "rgba(30,41,59,0.8)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 8, color: "#f1f5f9", fontSize: 13, outline: "none", padding: "9px 12px" };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h2 style={{ color: "#f1f5f9", fontSize: 20, fontWeight: 700, margin: 0 }}>Create Purchase Order</h2>
          <p style={{ color: "#64748b", fontSize: 13, margin: "4px 0 0" }}>Fill in the details below to create a new PO</p>
        </div>
        <button onClick={onCancel} style={{ padding: "8px 16px", background: "rgba(30,41,59,0.8)", border: "1px solid rgba(99,102,241,0.25)", borderRadius: 8, color: "#94a3b8", fontSize: 13, cursor: "pointer" }}>← Back</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Vendor *</label>
          <select value={vendorId} onChange={e => setVendorId(e.target.value)} style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }}>
            <option value="">Select a vendor...</option>
            {vendors.map(v => <option key={v.id} value={v.id}>{v.name} — ★{v.rating}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: "block", color: "#94a3b8", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Notes</label>
          <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }} />
        </div>
      </div>
      <div style={{ background: "rgba(15,23,42,0.6)", border: "1px solid rgba(99,102,241,0.15)", borderRadius: 14, overflow: "hidden", marginBottom: 20 }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(99,102,241,0.12)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>Line Items</span>
          <button onClick={addRow} style={{ padding: "6px 14px", background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 7, color: "#818cf8", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>+ Add Row</button>
        </div>
        <div style={{ padding: 16 }}>
          {rows.map((row, i) => {
            const product = getProduct(row.product_id);
            const lineTotal = product ? product.unit_price * row.quantity : 0;
            return (
              <div key={row.id} style={{ marginBottom: i < rows.length - 1 ? 16 : 0 }}>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr auto", gap: 10, alignItems: "end" }}>
                  <div>
                    <label style={{ display: "block", color: "#64748b", fontSize: 11, marginBottom: 5 }}>Product</label>
                    <select value={row.product_id} onChange={e => updateRow(row.id, "product_id", e.target.value)} style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }}>
                      <option value="">Select product...</option>
                      {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: "block", color: "#64748b", fontSize: 11, marginBottom: 5 }}>Qty</label>
                    <input type="number" min={1} value={row.quantity} onChange={e => updateRow(row.id, "quantity", e.target.value)} style={{ ...inputStyle, width: "100%", boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", color: "#64748b", fontSize: 11, marginBottom: 5 }}>Unit Price</label>
                    <div style={{ ...inputStyle, color: "#94a3b8" }}>{product ? fmt(product.unit_price) : "—"}</div>
                  </div>
                  <div>
                    <label style={{ display: "block", color: "#64748b", fontSize: 11, marginBottom: 5 }}>Line Total</label>
                    <div style={{ ...inputStyle, color: lineTotal > 0 ? "#10b981" : "#64748b", fontWeight: 600 }}>{lineTotal > 0 ? fmt(lineTotal) : "—"}</div>
                  </div>
                  <div>
                    <div style={{ marginBottom: 5, height: 16 }} />
                    <button onClick={() => removeRow(row.id)} disabled={rows.length === 1} style={{ padding: "9px 11px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 8, color: "#ef4444", cursor: rows.length === 1 ? "not-allowed" : "pointer", opacity: rows.length === 1 ? 0.3 : 1, fontSize: 14 }}>✕</button>
                  </div>
                </div>
                {row.product_id && (
                  <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "flex-start" }}>
                    <button onClick={() => handleAutoDesc(row.id, row.product_id)} disabled={aiLoading[row.id]} style={{ padding: "5px 12px", background: "linear-gradient(135deg, rgba(139,92,246,0.2), rgba(99,102,241,0.2))", border: "1px solid rgba(139,92,246,0.4)", borderRadius: 6, color: "#a78bfa", fontSize: 11, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap", display: "flex", alignItems: "center", gap: 5 }}>
                      {aiLoading[row.id] ? "✨ Generating..." : "✨ Auto-Description"}
                    </button>
                    {aiDesc[row.id] && <div style={{ background: "rgba(139,92,246,0.08)", border: "1px solid rgba(139,92,246,0.2)", borderRadius: 6, padding: "6px 10px", fontSize: 12, color: "#c4b5fd", flex: 1, lineHeight: 1.5 }}>{aiDesc[row.id]}</div>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 24 }}>
        <div style={{ background: "rgba(15,23,42,0.8)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 12, padding: "16px 24px", minWidth: 280 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#94a3b8", marginBottom: 8 }}><span>Subtotal</span><span>{fmt(subtotal)}</span></div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#f59e0b", marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid rgba(99,102,241,0.15)" }}><span>GST / Tax (5%)</span><span>+ {fmt(tax)}</span></div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 17, color: "#f1f5f9", fontWeight: 700 }}><span>Total</span><span style={{ color: "#818cf8" }}>{fmt(total)}</span></div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <button onClick={onCancel} style={{ padding: "12px 24px", background: "transparent", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 10, color: "#94a3b8", fontSize: 14, cursor: "pointer", fontWeight: 500 }}>Cancel</button>
        <button onClick={handleSubmit} disabled={submitting || subtotal === 0} style={{ padding: "12px 32px", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", border: "none", borderRadius: 10, color: "white", fontSize: 14, fontWeight: 600, cursor: submitting || subtotal === 0 ? "not-allowed" : "pointer", opacity: submitting || subtotal === 0 ? 0.6 : 1, boxShadow: "0 4px 16px rgba(99,102,241,0.4)" }}>
          {submitting ? "Creating PO..." : "Create Purchase Order"}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("dashboard");
  const [vendors, setVendors] = useState([]);
  const [products, setProducts] = useState([]);
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPO, setSelectedPO] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = "success") => setToast({ msg, type });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [v, p, o] = await Promise.all([api.get("/vendors"), api.get("/products"), api.get("/purchase-orders")]);
      setVendors(v); setProducts(p); setPos(o);
    } catch {
      setVendors(MOCK.vendors); setProducts(MOCK.products); setPos(MOCK.pos);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (user) loadData(); }, [user, loadData]);

  const handleLogin = ({ user }) => setUser(user);
  const handleLogout = () => { setUser(null); api.setToken(null); };

  const handleCreatePO = async (data) => {
    try {
      let newPO;
      try { newPO = await api.post("/purchase-orders", data); }
      catch {
        const vendor = vendors.find(v => v.id === data.vendor_id);
        const items = data.items.map(item => { const p = products.find(pr => pr.id === item.product_id); return { product: p, quantity: item.quantity, unit_price: p.unit_price, line_total: p.unit_price * item.quantity }; });
        const subtotal = items.reduce((s, i) => s + i.line_total, 0);
        const tax = subtotal * 0.05;
        newPO = { id: Date.now(), reference_no: `PO-${Date.now().toString().slice(-8)}`, vendor, vendor_id: data.vendor_id, subtotal, tax_amount: tax, total_amount: subtotal + tax, status: "DRAFT", notes: data.notes, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), line_items: items };
      }
      setPos(prev => [newPO, ...prev]);
      setView("dashboard");
      showToast(`✅ PO ${newPO.reference_no} created successfully!`);
    } catch (err) { showToast(`Failed to create PO: ${err.message}`, "error"); }
  };

  const handleUpdateStatus = async (poId, status) => {
    try {
      try { const updated = await api.patch(`/purchase-orders/${poId}/status`, { status }); setPos(prev => prev.map(po => po.id === poId ? updated : po)); }
      catch { setPos(prev => prev.map(po => po.id === poId ? { ...po, status } : po)); }
      showToast(`Status updated to ${STATUS_CONFIG[status]?.label}`);
    } catch (err) { showToast(`Failed: ${err.message}`, "error"); }
  };

  if (!user) return <LoginScreen onLogin={handleLogin} />;

  return (
    <div style={{ minHeight: "100vh", background: "#080d1a", fontFamily: "'Sora', 'DM Sans', sans-serif", color: "#f1f5f9" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&display=swap');
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        * { box-sizing: border-box; }
        select option { background: #1e293b; }
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: #0f172a; } ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
      `}</style>
      <div style={{ background: "rgba(8,13,26,0.95)", borderBottom: "1px solid rgba(99,102,241,0.15)", padding: "0 32px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 60, position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(12px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>📦</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#f1f5f9", lineHeight: 1 }}>PO Management</div>
            <div style={{ fontSize: 10, color: "#475569", lineHeight: 1 }}>IV Innovations Pvt Ltd</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {["dashboard", "create"].map(v => (
            <button key={v} onClick={() => setView(v)} style={{ padding: "6px 16px", background: view === v ? "rgba(99,102,241,0.2)" : "transparent", border: "1px solid", borderColor: view === v ? "rgba(99,102,241,0.4)" : "transparent", borderRadius: 8, color: view === v ? "#818cf8" : "#64748b", fontSize: 13, fontWeight: 500, cursor: "pointer", textTransform: "capitalize" }}>{v === "create" ? "New PO" : "Dashboard"}</button>
          ))}
          <div style={{ width: 1, height: 20, background: "rgba(99,102,241,0.2)", margin: "0 8px" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>{user.name?.[0]?.toUpperCase() || "U"}</div>
            <span style={{ fontSize: 13, color: "#94a3b8" }}>{user.name || user.email}</span>
          </div>
          <button onClick={handleLogout} style={{ padding: "6px 12px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 7, color: "#f87171", fontSize: 12, cursor: "pointer" }}>Sign out</button>
        </div>
      </div>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 24px" }}>
        {view === "dashboard" && <Dashboard pos={pos} loading={loading} onCreateNew={() => setView("create")} onViewPO={setSelectedPO} onUpdateStatus={handleUpdateStatus} />}
        {view === "create" && <CreatePOForm vendors={vendors} products={products} onSubmit={handleCreatePO} onCancel={() => setView("dashboard")} />}
      </div>
      {selectedPO && <PODetailModal po={selectedPO} onClose={() => setSelectedPO(null)} />}
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}