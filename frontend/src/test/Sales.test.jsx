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

test("switching period keeps the chosen dates and explains whole-week grouping", async () => {
  const urls = [];
  vi.stubGlobal("fetch", (url) => {
    urls.push(String(url));
    const weekly = String(url).includes("period=week");
    return reply(weekly ? { ...report, period: "week", start: "2026-08-31", end: "2026-10-11" } : report);
  });
  render(<MemoryRouter><SalesReport /></MemoryRouter>);
  await screen.findByRole("button", { name: "Weekly" });
  const from = screen.getByLabelText("From");
  const to = screen.getByLabelText("To");
  fireEvent.change(from, { target: { value: "2026-09-05" } });
  fireEvent.change(to, { target: { value: "2026-10-05" } });
  await userEvent.click(screen.getByRole("button", { name: "Weekly" }));
  expect(await screen.findByText(/whole weeks/)).toBeInTheDocument();
  expect(from).toHaveValue("2026-09-05");   // the user's dates are untouched
  expect(to).toHaveValue("2026-10-05");
  expect(urls.at(-1)).toContain("from=2026-09-05");
  expect(urls.at(-1)).toContain("to=2026-10-05");
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
    if (url.includes("/products/")) return reply([{ id: 1, name: "Cake", total_cost: "100.00" }]);
    if (init?.method === "POST") return reply({ id: 9 }, 201);
    return reply([]);
  });
  render(<MemoryRouter><Sales /></MemoryRouter>);

  await screen.findByRole("option", { name: "Cake" });
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  await userEvent.clear(screen.getByLabelText("Quantity"));
  await userEvent.type(screen.getByLabelText("Quantity"), "3");
  expect(screen.getByLabelText(/Selling price/)).toHaveValue(100);  // starts at the cost
  await userEvent.clear(screen.getByLabelText(/Selling price/));
  await userEvent.type(screen.getByLabelText(/Selling price/), "150");
  await userEvent.click(screen.getByRole("button", { name: "Record sale" }));

  expect(await screen.findByText("Sale recorded.")).toBeInTheDocument();
  const post = calls.find(([m]) => m === "POST");
  expect(JSON.parse(post[2])).toMatchObject({ product: 1, quantity: 3, unit_price: "150" });
});

test("the Sell link opens the form with that product chosen", async () => {
  vi.stubGlobal("fetch", (url) =>
    url.includes("/products/") ? reply([{ id: 1, name: "Cake", total_cost: "100.00" }, { id: 2, name: "Pie", total_cost: "50.00" }]) : reply([]));
  render(<MemoryRouter initialEntries={["/sales?product=2"]}><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Pie" });
  expect(screen.getByLabelText("Product")).toHaveValue("2");
  expect(screen.getByLabelText(/Selling price/)).toHaveValue(50);
});

test("selling price defaults to cost, follows the product until edited, then stays", async () => {
  vi.stubGlobal("fetch", (url) =>
    url.includes("/products/") ? reply([{ id: 1, name: "Cake", total_cost: "100.00" }, { id: 2, name: "Pie", total_cost: "50.00" }]) : reply([]));
  render(<MemoryRouter><Sales /></MemoryRouter>);
  await screen.findByRole("option", { name: "Cake" });
  const price = screen.getByLabelText(/Selling price/);
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  expect(price).toHaveValue(100);
  await userEvent.selectOptions(screen.getByLabelText("Product"), "2");
  expect(price).toHaveValue(50);          // untouched, so it follows the product
  await userEvent.clear(price);
  await userEvent.type(price, "75");
  await userEvent.selectOptions(screen.getByLabelText("Product"), "1");
  expect(price).toHaveValue(75);          // your own price is kept
});

test("server errors appear on the form", async () => {
  vi.stubGlobal("fetch", (url, init) => {
    if (url.includes("/products/")) return reply([{ id: 1, name: "Cake", total_cost: "100.00" }]);
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
