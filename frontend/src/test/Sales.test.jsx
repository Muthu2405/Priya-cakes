import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Sales from "../pages/Sales.jsx";
import SalesReport from "../pages/SalesReport.jsx";

const reply = (body, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
const row = (o) => ({ orders: 0, units: 0, revenue: "0.00", cost: "0.00", profit: "0.00", ...o });

const report = {
  period: "day", start: "2026-09-14", end: "2026-09-16",
  totals: row({ orders: 3, units: 4, revenue: "650.00", cost: "400.00", profit: "250.00" }),
  series: [
    row({ period_start: "2026-09-14", label: "14 Sep 2026", orders: 2, units: 3, revenue: "450.00", cost: "300.00", profit: "150.00" }),
    row({ period_start: "2026-09-15", label: "15 Sep 2026" }),
    row({ period_start: "2026-09-16", label: "16 Sep 2026", orders: 1, units: 1, revenue: "200.00", cost: "100.00", profit: "100.00" }),
  ],
  by_product: [row({ product: 1, product_name: "Cake", units: 4, revenue: "650.00", profit: "250.00" })],
};

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

test("report shows totals and requests the chosen period", async () => {
  const urls = [];
  vi.stubGlobal("fetch", (url) => { urls.push(url); return reply(report); });
  render(<MemoryRouter><SalesReport /></MemoryRouter>);

  expect((await screen.findAllByText("₹650.00")).length).toBeGreaterThan(0);
  expect(screen.getByText("Units sold").nextSibling).toHaveTextContent("4");
  expect(screen.getByRole("columnheader", { name: "Day" })).toBeInTheDocument();
  expect(screen.getByText("Cake")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Monthly" }));
  await screen.findByRole("columnheader", { name: "Month" });
  expect(urls.at(-1)).toContain("period=month");
});

test("switching period keeps the chosen dates; weeks show 7-day ranges", async () => {
  const urls = [];
  vi.stubGlobal("fetch", (url) => {
    urls.push(String(url));
    const weekly = String(url).includes("period=week");
    return reply(weekly ? {
      ...report, period: "week", start: "2026-09-29", end: "2026-10-05",
      series: [row({ period_start: "2026-09-29", period_end: "2026-10-05", days: 7, label: "29 Sep 2026 \u2013 5 Oct 2026", orders: 1, units: 1, revenue: "100.00" })],
      totals: row({ orders: 1, units: 1, revenue: "100.00" }),
    } : report);
  });
  render(<MemoryRouter><SalesReport /></MemoryRouter>);
  await screen.findByRole("button", { name: "Weekly" });
  const from = screen.getByLabelText("From");
  const to = screen.getByLabelText("To");
  fireEvent.change(from, { target: { value: "2026-09-29" } });
  fireEvent.change(to, { target: { value: "2026-10-05" } });
  await userEvent.click(screen.getByRole("button", { name: "Weekly" }));
  expect(await screen.findByText(/29 Sep 2026 – 5 Oct 2026/)).toBeInTheDocument();
  expect(screen.getByText("· 7 days")).toBeInTheDocument();
  expect(from).toHaveValue("2026-09-29");   // the user's dates are untouched
  expect(to).toHaveValue("2026-10-05");
  expect(urls.at(-1)).toContain("from=2026-09-29");
  expect(urls.at(-1)).toContain("to=2026-10-05");
});

test("report explains sales that have no cost", async () => {
  vi.stubGlobal("fetch", () => reply({ ...report, totals: { ...report.totals, no_cost_orders: 2 } }));
  render(<MemoryRouter><SalesReport /></MemoryRouter>);
  expect(await screen.findByText(/2 sales of products with no cost entered/)).toBeInTheDocument();
});

test("report with no sales shows an empty state", async () => {
  vi.stubGlobal("fetch", () => reply({ ...report, totals: row({}), series: [], by_product: [] }));
  render(<MemoryRouter><SalesReport /></MemoryRouter>);
  expect(await screen.findByText("No sales in this range")).toBeInTheDocument();
});

test("recording a sale posts the form and refreshes the list", async () => {
  const calls = [];
  vi.stubGlobal("fetch", (url, init) => {
    calls.push([init?.method ?? "GET", String(url), init?.body]);
    if (url.includes("/products/")) return reply([{ id: 1, name: "Cake", total_cost: "100.00", selling_price: "130.00" }]);
    if (init?.method === "POST") return reply({ id: 9 }, 201);
    return reply([]);
  });
  render(<MemoryRouter><Sales /></MemoryRouter>);

  await screen.findByRole("option", { name: "Cake" });
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  await userEvent.clear(screen.getByLabelText("Quantity"));
  await userEvent.type(screen.getByLabelText("Quantity"), "3");
  expect(screen.getByLabelText(/Selling price/)).toHaveValue(130);  // starts at the selling price (cost + profit)
  await userEvent.clear(screen.getByLabelText(/Selling price/));
  await userEvent.type(screen.getByLabelText(/Selling price/), "150");
  await userEvent.click(screen.getByRole("button", { name: "Record sale" }));

  expect(await screen.findByText("Sale recorded.")).toBeInTheDocument();
  const post = calls.find(([m]) => m === "POST");
  expect(JSON.parse(post[2])).toMatchObject({ product: 1, quantity: 3, unit_price: "150" });
});

test("the Sell link opens the form with that product chosen", async () => {
  vi.stubGlobal("fetch", (url) =>
    url.includes("/products/") ? reply([{ id: 1, name: "Cake", total_cost: "100.00", selling_price: "130.00" }, { id: 2, name: "Pie", total_cost: "50.00", selling_price: "65.00" }]) : reply([]));
  render(<MemoryRouter initialEntries={["/sales?product=2"]}><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Pie" });
  expect(screen.getByLabelText("Product")).toHaveValue("2");
  expect(screen.getByLabelText(/Selling price/)).toHaveValue(65);
});

test("selling price defaults to the product's selling price, follows the product until edited, then stays", async () => {
  vi.stubGlobal("fetch", (url) =>
    url.includes("/products/") ? reply([{ id: 1, name: "Cake", total_cost: "100.00", selling_price: "130.00" }, { id: 2, name: "Pie", total_cost: "50.00", selling_price: "65.00" }]) : reply([]));
  render(<MemoryRouter><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Cake" });
  const price = screen.getByLabelText(/Selling price/);
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  expect(price).toHaveValue(130);
  await userEvent.selectOptions(screen.getByLabelText("Product"), "2");
  expect(price).toHaveValue(65);          // untouched, so it follows the product
  await userEvent.clear(price);
  await userEvent.type(price, "75");
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  expect(price).toHaveValue(75);          // your own price is kept
});

test("a product that isn't in the list can be sold, with its own name and optional cost", async () => {
  const calls = [];
  vi.stubGlobal("fetch", (url, init) => {
    calls.push([init?.method ?? "GET", String(url), init?.body]);
    if (url.includes("/products/")) return reply([{ id: 1, name: "Cake", total_cost: "100.00", selling_price: "130.00" }]);
    if (init?.method === "POST") return reply({ id: 9 }, 201);
    return reply([]);
  });
  render(<MemoryRouter><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Cake" });
  expect(screen.queryByLabelText("Product name")).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Product"), "Another product (not in my list)…");
  await userEvent.type(screen.getByLabelText("Product name"), "Brownie");
  await userEvent.type(screen.getByLabelText(/Selling price/), "40");
  await userEvent.type(screen.getByLabelText(/Cost each/), "25");
  expect(screen.getByText(/Profit on this sale/)).toHaveTextContent("₹15.00");
  await userEvent.click(screen.getByRole("button", { name: "Record sale" }));
  expect(await screen.findByText("Sale recorded.")).toBeInTheDocument();
  expect(JSON.parse(calls.find(([m]) => m === "POST")[2])).toMatchObject(
    { product: null, product_name: "Brownie", unit_price: "40", unit_cost: "25", quantity: 1 });
});

test("the list fills profit for known products and shows a dash when cost is unknown", async () => {
  const sale = (o) => ({ id: 1, product: 1, in_catalog: true, sold_on: "2026-10-01", quantity: 2, unit_price: "130.00",
    revenue: "260.00", cost: "200.00", profit: "60.00", ...o });
  vi.stubGlobal("fetch", (url) => url.includes("/products/") ? reply([]) : reply([
    sale({ product_name: "Cake" }),
    sale({ id: 2, product: null, in_catalog: false, product_name: "Brownie", unit_price: "40.00", revenue: "80.00", cost: null, profit: null }),
  ]));
  render(<MemoryRouter><Sales /></MemoryRouter>);
  expect(await screen.findByText("₹60.00")).toBeInTheDocument();
  expect(screen.getByText("Brownie")).toBeInTheDocument();
  expect(screen.getByText(/not in products/)).toBeInTheDocument();
  expect(screen.getByTitle("Add a cost to see profit")).toHaveTextContent("—");
});

test("server errors appear on the form", async () => {
  vi.stubGlobal("fetch", (url, init) => {
    if (url.includes("/products/")) return reply([{ id: 1, name: "Cake", total_cost: "100.00", selling_price: "130.00" }]);
    if (init?.method === "POST") return reply({ sold_on: ["A sale can't be dated in the future."] }, 400);
    return reply([]);
  });
  render(<MemoryRouter><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Cake" });
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  await userEvent.clear(screen.getByLabelText(/Selling price/));
  await userEvent.type(screen.getByLabelText(/Selling price/), "10");
  await userEvent.click(screen.getByRole("button", { name: "Record sale" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("future");
});
