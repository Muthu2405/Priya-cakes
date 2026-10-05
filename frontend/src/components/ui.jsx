const rupee = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

// API values are exact decimal strings; Number() is for display only.
export const inr = (v) => rupee.format(Number(v ?? 0));
export const qty = (v) => (v === "" || v == null ? "" : String(Number(v)));
export const dateLabel = (iso) =>
  new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export const UNITS = ["kg", "g", "L", "ml", "pcs"];
const FAMILY = { kg: "weight", g: "weight", L: "volume", ml: "volume", pcs: "count" };
export const compatibleUnits = (unit) => UNITS.filter((u) => FAMILY[u] === FAMILY[unit]);

export function Notice({ kind = "error", children, onClose }) {
  if (!children) return null;
  return (
    <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span>{children}</span>
      {onClose && (
        <button type="button" className="link" onClick={onClose}>Dismiss</button>
      )}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
