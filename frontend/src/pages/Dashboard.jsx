import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api.js";
import { Empty, Notice, dateLabel, inr } from "../components/ui.jsx";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.listIngredients({ active: "true" }), api.listProducts()])
      .then(([ingredients, products]) => setData({ ingredients, products }))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-head">
        <h1>What does it cost to make?</h1>
        <div className="actions">
          <Link className="btn primary" to="/products/new">New product</Link>
          <Link className="btn" to="/ingredients">Add ingredient</Link>
        </div>
      </div>

      <Notice>{error}</Notice>

      {data && (
        <>
          <p className="summary">
            <strong>{data.ingredients.length}</strong> ingredients priced,{" "}
            <strong>{data.products.length}</strong> products costed.
          </p>

          <section className="card">
            <h2>Recent products</h2>
            {data.products.length === 0 ? (
              <Empty title="No products yet">
                Add your ingredient prices first, then cost your first product.
              </Empty>
            ) : (
              <table>
                <thead>
                  <tr><th>Product</th><th className="num">Final cost</th><th>Saved</th></tr>
                </thead>
                <tbody>
                  {data.products.slice(0, 5).map((p) => (
                    <tr key={p.id}>
                      <td><Link to={`/products/${p.id}`}>{p.name}</Link></td>
                      <td className="num">{inr(p.total_cost)}</td>
                      <td>{dateLabel(p.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </>
  );
}
