import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api.js";
import { Empty, Notice, inr } from "../components/ui.jsx";

const PERIODS = [
  { id: "day", label: "Daily" },
  { id: "week", label: "Weekly" },
  { id: "month", label: "Monthly" },
];

const iso = (d) => d.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
const daysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };
const shortDate = (v) => new Date(`${v}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export default function SalesReport() {
  const [period, setPeriod] = useState("day");
  // The range is the user's own and stays put when switching Daily / Weekly / Monthly.
  const [from, setFrom] = useState(() => daysAgo(27))  // 28 days = four 7-day weeks, ending today;
  const [to, setTo] = useState(() => iso(new Date()));
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const params = { period, from, to };

  useEffect(() => {
    let current = true;  // ignore answers to requests we've since replaced
    setError("");
    api.salesReport({ period, from, to })
      .then((r) => current && setReport(r))
      .catch((e) => current && setError(e.message));
    return () => { current = false; };
  }, [period, from, to]);

  function choosePeriod(id) {
    if (id === period) return;
    setReport(null);  // don't show the old period's rows under the new tab
    setPeriod(id);
  }

  // Ignore a cleared date box rather than letting it fall back to a different range.
  const pick = (setter) => (e) => e.target.value && setter(e.target.value);

  async function exportCsv() {
    setBusy(true);
    try {
      await api.downloadSalesCsv(params);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const totals = report?.totals;
  const max = report ? Math.max(...report.series.map((r) => Number(r.revenue)), 0) : 0;

  return (
    <>
      <div className="page-head">
        <h1>Sales report</h1>
        <div className="actions">
          <Link className="btn" to="/sales">Record a sale</Link>
          <button type="button" className="btn primary" onClick={exportCsv} disabled={busy || !report}>
            {busy ? "Preparing…" : "Download CSV"}
          </button>
        </div>
      </div>

      <section className="card">
        <div className="filters">
          <div className="tabs" role="group" aria-label="Report period">
            {PERIODS.map((p) => (
              <button key={p.id} type="button" className={period === p.id ? "tab on" : "tab"}
                aria-pressed={period === p.id} onClick={() => choosePeriod(p.id)}>
                {p.label}
              </button>
            ))}
          </div>
          <label>From
            <input type="date" value={from} max={to} onChange={pick(setFrom)} />
          </label>
          <label>To
            <input type="date" value={to} min={from} onChange={pick(setTo)} />
          </label>
        </div>
        <Notice>{error}</Notice>
        {report && period === "month" && (report.start !== from || report.end !== to) && (
          <p className="muted">
            Grouped into whole months, so this report covers {shortDate(report.start)} to {shortDate(report.end)}.
          </p>
        )}
        {period === "week" && (
          <p className="muted">Weeks are 7 days each, counted from your From date. The last week is shorter if it runs past the To date.</p>
        )}

        {!report ? (
          !error && <p className="muted">Loading report…</p>
        ) : (
          <>
            <div className="kpis">
              <div><span>Revenue</span><strong>{inr(totals.revenue)}</strong></div>
              <div><span>Cost</span><strong>{inr(totals.cost)}</strong></div>
              <div><span>Profit</span><strong className={Number(totals.profit) < 0 ? "loss" : ""}>{inr(totals.profit)}</strong></div>
              <div><span>Units sold</span><strong>{totals.units}</strong></div>
              <div><span>Sales</span><strong>{totals.orders}</strong></div>
            </div>
            {totals.no_cost_orders > 0 && (
              <p className="muted">
                {totals.no_cost_orders} sale{totals.no_cost_orders === 1 ? "" : "s"} of products with no cost entered
                {" "}count in revenue but not in cost or profit.
              </p>
            )}

            {totals.orders === 0 ? (
              <Empty title="No sales in this range">
                Saving a product only costs it. Reports count sales you record on the{" "}
                <Link to="/sales">Sales page</Link>. Record one, or widen the dates.
              </Empty>
            ) : (
              <>
                <ol className="bars" aria-label="Revenue by period">
                  {report.series.map((r) => (
                    <li key={r.period_start} title={`${r.label}: ${inr(r.revenue)}`}>
                      <i style={{ height: `${max ? Math.max((Number(r.revenue) / max) * 100, r.orders ? 3 : 0) : 0}%` }} />
                    </li>
                  ))}
                </ol>

                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>{{ day: "Day", week: "Week", month: "Month" }[period]}</th>
                        <th className="num">Sales</th><th className="num">Units</th>
                        <th className="num">Revenue</th><th className="num">Cost</th><th className="num">Profit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...report.series].reverse().map((r) => (
                        <tr key={r.period_start} className={r.orders ? "" : "inactive"}>
                          <td>{r.label}{period === "week" && <small className="muted"> · {r.days} day{r.days === 1 ? "" : "s"}</small>}</td>
                          <td className="num">{r.orders}</td>
                          <td className="num">{r.units}</td>
                          <td className="num">{inr(r.revenue)}</td>
                          <td className="num">{inr(r.cost)}</td>
                          <td className={`num ${Number(r.profit) < 0 ? "loss" : ""}`}>{inr(r.profit)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </section>

      {report && report.by_product.length > 0 && (
        <section className="card">
          <h2>By product</h2>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Product</th><th className="num">Units</th><th className="num">Revenue</th><th className="num">Profit</th></tr>
              </thead>
              <tbody>
                {report.by_product.map((p) => (
                  <tr key={p.product ?? p.product_name}>
                    <td>{p.product_name}{!p.in_catalog && <small className="muted"> · not in products</small>}</td>
                    <td className="num">{p.units}</td>
                    <td className="num">{inr(p.revenue)}</td>
                    <td className={`num ${Number(p.profit) < 0 ? "loss" : ""}`}>{inr(p.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
