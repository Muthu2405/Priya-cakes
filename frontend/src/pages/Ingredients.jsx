import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api.js";
import useDebounced from "../hooks/useDebounced.js";
import { Empty, Notice, UNITS, inr, qty } from "../components/ui.jsx";

const blank = { name: "", quantity: "1", unit: "kg", price: "", active: true };

export default function Ingredients() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const query = useDebounced(search);
  const [unit, setUnit] = useState("");
  const [showInactive, setShowInactive] = useState(false);

  const [form, setForm] = useState(blank);
  const [editingId, setEditingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      setItems(await api.listIngredients({ search: query, unit, active: showInactive ? "" : "true" }));
    } catch (e) {
      setError(e.message);
      setItems([]);
    }
  }, [query, unit, showInactive]);

  useEffect(() => { load(); }, [load]);

  const set = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const reset = () => { setForm(blank); setEditingId(null); setFormError(""); };

  const startEdit = (item) => {
    setEditingId(item.id);
    setForm({ name: item.name, quantity: qty(item.quantity), unit: item.unit, price: item.price, active: item.active });
    setFormError("");
    setNotice("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const body = { ...form, name: form.name.trim() };
      if (editingId) await api.updateIngredient(editingId, body);
      else await api.createIngredient(body);
      setNotice(editingId ? `Updated ${body.name}.` : `Added ${body.name}.`);
      reset();
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`Remove ${item.name}?`)) return;
    try {
      const res = await api.deleteIngredient(item.id);
      setNotice(res?.detail ?? `Deleted ${item.name}.`);
      if (editingId === item.id) reset();
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="page-head"><h1>Ingredients</h1></div>

      <form className="card form-grid" onSubmit={submit}>
        <h2>{editingId ? `Edit ${form.name || "ingredient"}` : "Add ingredient"}</h2>
        <label className="grow">Ingredient name
          <input value={form.name} onChange={set("name")} required maxLength={120} placeholder="Flour" />
        </label>
        <label>Quantity
          <input type="number" min="0.001" step="any" value={form.quantity} onChange={set("quantity")} required />
        </label>
        <label>Unit
          <select value={form.unit} onChange={set("unit")}>
            {UNITS.map((u) => <option key={u}>{u}</option>)}
          </select>
        </label>
        <label>Price (₹)
          <input type="number" min="0" step="0.01" value={form.price} onChange={set("price")} required placeholder="200" />
        </label>
        {editingId && (
          <label className="check">
            <input type="checkbox" checked={form.active} onChange={set("active")} /> Active
          </label>
        )}
        <div className="actions">
          <button className="btn primary" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Add ingredient"}
          </button>
          {editingId && <button type="button" className="btn" onClick={reset}>Cancel</button>}
        </div>
        <Notice>{formError}</Notice>
      </form>

      <Notice kind="info" onClose={() => setNotice("")}>{notice}</Notice>
      <Notice>{error}</Notice>

      <section className="card">
        <div className="filters">
          <label className="grow">Search
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name" />
          </label>
          <label>Unit
            <select value={unit} onChange={(e) => setUnit(e.target.value)}>
              <option value="">All units</option>
              {UNITS.map((u) => <option key={u}>{u}</option>)}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> Show inactive
          </label>
        </div>

        {items === null ? (
          <p className="muted">Loading ingredients…</p>
        ) : items.length === 0 ? (
          <Empty title="No ingredients found">
            {search || unit ? "Try a different search or unit." : "Add your first ingredient above, for example Flour, 1 kg, ₹200."}
          </Empty>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Ingredient</th><th className="num">Quantity</th><th>Unit</th><th className="num">Price</th><th /></tr>
              </thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.id} className={i.active ? "" : "inactive"}>
                    <td>{i.name}{!i.active && <small> (inactive)</small>}</td>
                    <td className="num">{qty(i.quantity)}</td>
                    <td>{i.unit}</td>
                    <td className="num">{inr(i.price)}</td>
                    <td className="row-actions">
                      <button type="button" className="link" onClick={() => startEdit(i)}>Edit</button>
                      <button type="button" className="link danger" onClick={() => remove(i)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
