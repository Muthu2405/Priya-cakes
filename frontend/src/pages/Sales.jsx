import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../services/api.js";
import { Empty, Notice, dateLabel, inr } from "../components/ui.jsx";

const OTHER = "__other"; // a product that isn't in the user's product list
const todayISO = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
const blank = () => ({ product: "", product_name: "", quantity: "1", unit_price: "", unit_cost: "", sold_on: todayISO() });

export default function Sales() {
  const [sales, setSales] = useState(null);
  const [products, setProducts] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [params] = useSearchParams();
  const [form, setForm] = useState(() => ({ ...blank(), product: params.get("product") ?? "" }));
  const [editingId, setEditingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const [s, p] = await Promise.all([api.listSales(), api.listProducts()]);
      setSales(s);
      setProducts(p);
    } catch (e) {
      setError(e.message);
      setSales([]);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // The selling price starts at the product's selling price (cost + profit);
  // typing a price of your own stops that.
  const [priceEdited, setPriceEdited] = useState(false);
  const priceOf = (id) => products.find((p) => String(p.id) === String(id))?.selling_price ?? "";

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  const setPrice = (e) => { setPriceEdited(true); set("unit_price")(e); };
  const chooseProduct = (e) => {
    const product = e.target.value;
    setForm((f) => ({ ...f, product, unit_price: priceEdited && f.unit_price !== "" ? f.unit_price : priceOf(product) }));
  };
  const reset = () => { setForm(blank()); setEditingId(null); setFormError(""); setPriceEdited(false); };

  // Arriving from a product's "Sell" link: fill the price once the products have loaded.
  useEffect(() => {
    if (!editingId && !priceEdited) {
      setForm((f) => (f.product && f.product !== OTHER && f.unit_price === "" ? { ...f, unit_price: priceOf(f.product) } : f));
    }
  }, [products]); // eslint-disable-line react-hooks/exhaustive-deps

  const startEdit = (s) => {
    setEditingId(s.id);
    setPriceEdited(true);  // keep the price this sale was recorded at
    setForm({
      product: s.product ? String(s.product) : OTHER,
      product_name: s.product ? "" : s.product_name,
      quantity: String(s.quantity),
      unit_price: s.unit_price,
      unit_cost: s.product ? "" : s.unit_cost ?? "",
      sold_on: s.sold_on,
    });
    setFormError("");
    setNotice("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const other = form.product === OTHER;
      const body = {
        quantity: Number(form.quantity),
        unit_price: form.unit_price,
        sold_on: form.sold_on,
        ...(other
          ? { product: null, product_name: form.product_name.trim(), unit_cost: form.unit_cost === "" ? null : form.unit_cost }
          : { product: Number(form.product) }),
      };
      if (editingId) await api.updateSale(editingId, body);
      else await api.createSale(body);
      setNotice(editingId ? "Sale updated." : "Sale recorded.");
      // keep the date so several sales for one day can be entered quickly
      setForm({ ...blank(), sold_on: form.sold_on });
      setEditingId(null);
      setPriceEdited(false);
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(s) {
    if (!window.confirm(`Delete this sale of ${s.quantity} × ${s.product_name}?`)) return;
    try {
      await api.deleteSale(s.id);
      if (editingId === s.id) reset();
      setNotice("Sale deleted.");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const isOther = form.product === OTHER;
  const chosen = products.find((p) => String(p.id) === form.product);
  const unitCost = isOther ? form.unit_cost : chosen?.total_cost;
  const liveProfit = unitCost !== undefined && unitCost !== "" && form.unit_price !== "" && Number(form.quantity) > 0
    ? Number(form.quantity) * (Number(form.unit_price) - Number(unitCost))
    : null;

  return (
    <>
      <div className="page-head">
        <h1>Sales</h1>
        <Link className="btn" to="/sales/report">View sales report</Link>
      </div>

      <form className="card form-grid" onSubmit={submit}>
        <h2>{editingId ? "Edit sale" : "Record a sale"}</h2>
        <label className="grow">Product
          <select value={form.product} onChange={chooseProduct} required>
            <option value="">Choose a product…</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            <option value={OTHER}>Another product (not in my list)…</option>
          </select>
        </label>
        {isOther && (
          <label className="grow">Product name
            <input value={form.product_name} onChange={set("product_name")} required maxLength={160} placeholder="Brownie" />
          </label>
        )}
        <label>Quantity
          <input type="number" min="1" step="1" value={form.quantity} onChange={set("quantity")} required />
        </label>
        <label>Selling price each (₹)
          <input type="number" min="0" step="0.01" value={form.unit_price} onChange={setPrice} required />
          {chosen && <small className="muted">Starts at the selling price ({inr(chosen.selling_price)}). Change it if you sold for less or more.</small>}
        </label>
        {isOther && (
          <label>Cost each (₹), optional
            <input type="number" min="0" step="0.01" value={form.unit_cost} onChange={set("unit_cost")} placeholder="Leave blank if unknown" />
            <small className="muted">Needed to work out profit.</small>
          </label>
        )}
        <label>Date
          <input type="date" value={form.sold_on} max={todayISO()} onChange={set("sold_on")} required />
        </label>
        {liveProfit !== null && (
          <p className={`grow ${liveProfit < 0 ? "loss" : "muted"}`}>Profit on this sale: <strong>{inr(liveProfit)}</strong></p>
        )}
        <div className="actions">
          <button className="btn primary" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Record sale"}
          </button>
          {editingId && <button type="button" className="btn" onClick={reset}>Cancel</button>}
        </div>
        <Notice>{formError}</Notice>
      </form>

      <Notice kind="info" onClose={() => setNotice("")}>{notice}</Notice>
      <Notice>{error}</Notice>

      <section className="card">
        <h2>Recent sales</h2>
        {sales === null ? (
          <p className="muted">Loading sales…</p>
        ) : sales.length === 0 ? (
          <Empty title="No sales yet">
            Record your first sale above to start your daily, weekly and monthly reports.
          </Empty>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th><th>Product</th><th className="num">Qty</th><th className="num">Price</th>
                  <th className="num">Revenue</th><th className="num">Profit</th><th />
                </tr>
              </thead>
              <tbody>
                {sales.slice(0, 50).map((s) => (
                  <tr key={s.id}>
                    <td>{dateLabel(s.sold_on)}</td>
                    <td>{s.product_name}{!s.in_catalog && <small className="muted"> · not in products</small>}</td>
                    <td className="num">{s.quantity}</td>
                    <td className="num">{inr(s.unit_price)}</td>
                    <td className="num">{inr(s.revenue)}</td>
                    <td className={`num ${s.profit !== null && Number(s.profit) < 0 ? "loss" : ""}`}>
                      {s.profit === null ? <span className="muted" title="Add a cost to see profit">—</span> : inr(s.profit)}
                    </td>
                    <td className="row-actions">
                      <button type="button" className="link" onClick={() => startEdit(s)}>Edit</button>
                      <button type="button" className="link danger" onClick={() => remove(s)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sales.length > 50 && <p className="muted">Showing the latest 50 sales. Use the report for totals.</p>}
          </div>
        )}
      </section>
    </>
  );
}
