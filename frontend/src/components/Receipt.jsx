import { inr, qty } from "./ui.jsx";

// Shared by the live preview (calculate response) and the saved product view.
export default function Receipt({ data, title, status, stale }) {
  if (!data) {
    return (
      <aside className="receipt receipt-empty">
        <p>{status || "Pick ingredients and enter the quantities used to see the costing here."}</p>
      </aside>
    );
  }
  const lines = data.lines ?? data.ingredients ?? [];

  return (
    <aside className={`receipt${stale ? " stale" : ""}`} aria-live="polite">
      <h2>{title || "Untitled product"}</h2>

      <ul className="leaders">
        {lines.map((l, i) => (
          <li key={i}>
            <span>{l.ingredient_name} <small>{qty(l.used_quantity)} {l.used_unit}</small></span>
            <i aria-hidden="true" />
            <b>{inr(l.calculated_cost)}</b>
          </li>
        ))}
      </ul>

      <ul className="leaders subtotal">
        <li><span>Ingredients</span><i aria-hidden="true" /><b>{inr(data.total_ingredient_cost)}</b></li>
        <li><span>Packaging</span><i aria-hidden="true" /><b>{inr(data.packaging_cost)}</b></li>
        <li><span>EB / electricity</span><i aria-hidden="true" /><b>{inr(data.eb_cost)}</b></li>
        <li><span>Labour</span><i aria-hidden="true" /><b>{inr(data.labour_cost)}</b></li>
      </ul>

      <div className="final">
        <span>Final cost</span>
        <strong>{inr(data.total_cost)}</strong>
      </div>
      {data.profit !== undefined && (
        <ul className="leaders subtotal">
          <li><span>Profit</span><i aria-hidden="true" /><b>{inr(data.profit)}</b></li>
          <li><span>Selling price</span><i aria-hidden="true" /><b>{inr(data.selling_price)}</b></li>
        </ul>
      )}
      {status && <p className="muted small">{status}</p>}
    </aside>
  );
}
