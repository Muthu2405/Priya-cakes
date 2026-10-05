import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api.js";
import useDebounced from "../hooks/useDebounced.js";
import Receipt from "../components/Receipt.jsx";
import { Notice, compatibleUnits, inr } from "../components/ui.jsx";

let nextKey = 1;
const newRow = (over = {}) => ({ key: nextKey++, ingredient: "", used_quantity: "", used_unit: "g", ...over });

export default function ProductCreate() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();

  const [ingredients, setIngredients] = useState([]);
  const [name, setName] = useState("");
  const [soldBy, setSoldBy] = useState("pcs");
  const [rows, setRows] = useState([newRow()]);
  const [extras, setExtras] = useState({ packaging_cost: "", eb_cost: "", labour_cost: "" });

  // Profit follows 30% of the cost until the user types their own amount.
  const [profit, setProfit] = useState("");
  const [profitEdited, setProfitEdited] = useState(false);

  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState({ data: null, error: "", loading: false });

  const byId = useMemo(() => new Map(ingredients.map((i) => [String(i.id), i])), [ingredients]);

  // Load ingredient choices (and the product when editing).
  useEffect(() => {
    (async () => {
      try {
        const list = await api.listIngredients({ active: "true" });
        setIngredients(list);
        if (editing) {
          const p = await api.getProduct(id);
          setName(p.name);
          setSoldBy(p.sold_by || "pcs");
          setExtras({
            packaging_cost: String(Number(p.packaging_cost)),
            eb_cost: String(Number(p.eb_cost)),
            labour_cost: String(Number(p.labour_cost)),
          });
          const auto = Math.round(Number(p.total_cost) * 30) / 100;
          if (Math.abs(Number(p.profit) - auto) > 0.005) {
            setProfit(String(Number(p.profit)));
            setProfitEdited(true);
          }
          setRows(p.ingredients.map((l) =>
            newRow({ ingredient: String(l.ingredient), used_quantity: String(Number(l.used_quantity)), used_unit: l.used_unit })
          ));
        }
      } catch (e) {
        setLoadError(e.message);
      }
    })();
  }, [id, editing]);

  const updateRow = (key, patch) => setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  function pickIngredient(key, value) {
    const ing = byId.get(value);
    updateRow(key, { ingredient: value, ...(ing ? { used_unit: ing.unit } : {}) });
  }

  const validRows = rows.filter((r) => r.ingredient && r.used_quantity !== "" && Number(r.used_quantity) >= 0);
  const buildBody = () => ({
    name: name.trim() || "Untitled product",
    sold_by: soldBy,
    packaging_cost: extras.packaging_cost || "0",
    eb_cost: extras.eb_cost || "0",
    labour_cost: extras.labour_cost || "0",
    ...(profitEdited ? { profit } : {}),
    ingredients: validRows.map((r) => ({
      ingredient: Number(r.ingredient),
      used_quantity: r.used_quantity,
      used_unit: r.used_unit,
    })),
  });

  // Live preview, debounced; ignores out-of-order responses.
  const snapshot = JSON.stringify({ name, soldBy, extras, validRows, profit: profitEdited ? profit : null });
  const settled = useDebounced(snapshot, 350);
  const latest = useRef(0);
  useEffect(() => {
    if (validRows.length === 0) {
      setPreview({ data: null, error: "", loading: false });
      return;
    }
    const ticket = ++latest.current;
    setPreview((p) => ({ ...p, loading: true }));
    api.calculate(buildBody())
      .then((data) => ticket === latest.current && setPreview({ data, error: "", loading: false }))
      .catch((e) => ticket === latest.current && setPreview((p) => ({ ...p, error: e.message, loading: false })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled]);

  // Map preview lines back to rows (same order as validRows).
  const costFor = (row) => {
    const idx = validRows.findIndex((r) => r.key === row.key);
    return idx >= 0 ? preview.data?.lines?.[idx]?.calculated_cost : undefined;
  };

  async function save(e) {
    e.preventDefault();
    setSaveError("");
    if (!name.trim()) return setSaveError("Enter a product name.");
    if (validRows.length === 0) return setSaveError("Add at least one ingredient with a quantity.");
    setSaving(true);
    try {
      const saved = editing ? await api.updateProduct(id, buildBody()) : await api.createProduct(buildBody());
      navigate(`/products/${saved.id}`);
    } catch (err) {
      setSaveError(err.message);
      setSaving(false);
    }
  }

  const setExtra = (field) => (e) => setExtras((x) => ({ ...x, [field]: e.target.value }));

  return (
    <>
      <div className="page-head">
        <h1>{editing ? "Edit product" : "New product"}</h1>
      </div>
      <Notice>{loadError}</Notice>

      <form className="costing" onSubmit={save}>
        <div className="costing-form">
          <section className="card form-grid">
            <label className="grow">Product name
              <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={160} placeholder="Chocolate cake" />
            </label>
            <label>Sold by
              <select value={soldBy} onChange={(e) => setSoldBy(e.target.value)}>
                <option value="pcs">pcs</option>
                <option value="kg">kg</option>
              </select>
            </label>
          </section>

          <section className="card">
            <h2>Ingredients</h2>
            {ingredients.length === 0 && !loadError && (
              <Notice kind="info">
                No ingredients yet. <Link to="/ingredients">Add ingredients</Link> first.
              </Notice>
            )}
            <div className="rows">
              {rows.map((r) => {
                const ing = byId.get(r.ingredient);
                const units = ing ? compatibleUnits(ing.unit) : ["g"];
                const cost = costFor(r);
                return (
                  <div className="row" key={r.key}>
                    <label className="grow">Ingredient
                      <select value={r.ingredient} onChange={(e) => pickIngredient(r.key, e.target.value)}>
                        <option value="">Choose…</option>
                        {ingredients.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                      </select>
                    </label>
                    <label>Quantity used
                      <input type="number" min="0" step="any" value={r.used_quantity}
                        onChange={(e) => updateRow(r.key, { used_quantity: e.target.value })} />
                    </label>
                    <label>Unit
                      <select value={r.used_unit} onChange={(e) => updateRow(r.key, { used_unit: e.target.value })} disabled={!ing}>
                        {units.map((u) => <option key={u}>{u}</option>)}
                      </select>
                    </label>
                    <div className="row-cost" aria-label="Cost">{cost !== undefined ? inr(cost) : "–"}</div>
                    <button type="button" className="link danger" disabled={rows.length === 1}
                      onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}>
                      Remove
                    </button>
                  </div>
                );
              })}
            </div>
            <button type="button" className="btn" onClick={() => setRows((rs) => [...rs, newRow()])}>Add ingredient</button>
          </section>

          <section className="card form-grid">
            <h2>Additional costs</h2>
            <label>Packaging (₹)
              <input type="number" min="0" step="0.01" value={extras.packaging_cost} onChange={setExtra("packaging_cost")} placeholder="0" />
            </label>
            <label>EB / electricity (₹)
              <input type="number" min="0" step="0.01" value={extras.eb_cost} onChange={setExtra("eb_cost")} placeholder="0" />
            </label>
            <label>Labour (₹)
              <input type="number" min="0" step="0.01" value={extras.labour_cost} onChange={setExtra("labour_cost")} placeholder="0" />
            </label>
          </section>

          <section className="card form-grid">
            <h2>Profit</h2>
            <label>Profit (₹)
              <input type="number" min="0" step="0.01"
                value={profitEdited ? profit : preview.data?.default_profit ?? ""}
                onChange={(e) => {
                  // clearing the box goes back to the automatic 30%
                  setProfit(e.target.value);
                  setProfitEdited(e.target.value !== "");
                }}
                placeholder="30% of cost" />
            </label>
            <p className="muted small grow">
              {profitEdited
                ? <>Your own amount. <button type="button" className="link" onClick={() => { setProfit(""); setProfitEdited(false); }}>Use 30% of cost</button></>
                : "Filled in as 30% of the final cost. Type a different amount to change it."}
            </p>
          </section>

          <Notice>{saveError}</Notice>
          <div className="actions">
            <button className="btn primary" disabled={saving}>
              {saving ? "Saving…" : editing ? "Save changes" : "Save product"}
            </button>
            <Link className="btn" to={editing ? `/products/${id}` : "/products"}>Cancel</Link>
          </div>
        </div>

        <div className="costing-receipt">
          <Receipt
            data={preview.data}
            title={name.trim()}
            stale={preview.loading}
            status={preview.error || undefined}
          />
        </div>
      </form>
    </>
  );
}
