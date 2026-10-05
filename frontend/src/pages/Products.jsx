import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api.js";
import useDebounced from "../hooks/useDebounced.js";
import { Empty, Notice, dateLabel, inr } from "../components/ui.jsx";

export default function Products() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const query = useDebounced(search);

  const load = useCallback(async () => {
    try {
      setError("");
      setItems(await api.listProducts({ search: query }));
    } catch (e) {
      setError(e.message);
      setItems([]);
    }
  }, [query]);

  useEffect(() => { load(); }, [load]);

  async function remove(p) {
    if (!window.confirm(`Delete ${p.name}? This can't be undone.`)) return;
    try {
      await api.deleteProduct(p.id);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Products</h1>
        <Link className="btn primary" to="/products/new">New product</Link>
      </div>
      <Notice>{error}</Notice>

      <section className="card">
        <div className="filters">
          <label className="grow">Search
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name" />
          </label>
        </div>

        {items === null ? (
          <p className="muted">Loading products…</p>
        ) : items.length === 0 ? (
          <Empty title={search ? "No matching products" : "No products yet"}>
            {search ? "Try a different name." : "Create a product to see its full costing here."}
          </Empty>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>Product</th><th className="num">Final cost</th><th>Saved</th><th />
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id}>
                    <td><Link to={`/products/${p.id}`}>{p.name}</Link></td>
                    <td className="num">{inr(p.total_cost)}</td>
                    <td>{dateLabel(p.created_at)}</td>
                    <td className="row-actions">
                      <Link className="link" to={`/sales?product=${p.id}`}>Sell</Link>
                      <Link className="link" to={`/products/${p.id}/edit`}>Edit</Link>
                      <button type="button" className="link danger" onClick={() => remove(p)}>Delete</button>
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
