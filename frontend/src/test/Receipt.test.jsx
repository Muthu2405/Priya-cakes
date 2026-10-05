import { render, screen } from "@testing-library/react";
import Receipt from "../components/Receipt.jsx";

const data = {
  lines: [
    { ingredient_name: "Flour", used_quantity: "100.000", used_unit: "g", calculated_cost: "20.00" },
    { ingredient_name: "Egg", used_quantity: "3.000", used_unit: "pcs", calculated_cost: "18.00" },
  ],
  total_ingredient_cost: "38.00",
  packaging_cost: "10.00",
  eb_cost: "5.00",
  other_cost: "2.00",
  total_cost: "55.00",
};

test("shows each ingredient line and the final cost", () => {
  render(<Receipt data={data} title="Cake" />);
  expect(screen.getByRole("heading", { name: "Cake" })).toBeInTheDocument();
  expect(screen.getByText("Flour")).toBeInTheDocument();
  expect(screen.getByText("₹20.00")).toBeInTheDocument();
  expect(screen.getByText("₹18.00")).toBeInTheDocument();
  expect(screen.getByText("₹55.00")).toBeInTheDocument();
  expect(screen.getByText("100 g")).toBeInTheDocument();
});

test("has no per-piece figure", () => {
  render(<Receipt data={data} title="Cake" />);
  expect(screen.queryByText(/per piece/i)).not.toBeInTheDocument();
});

test("shows a hint when there is nothing to cost yet", () => {
  render(<Receipt data={null} />);
  expect(screen.getByText(/pick ingredients/i)).toBeInTheDocument();
});

test("shows the error message when the preview fails", () => {
  render(<Receipt data={null} status="Flour is priced in kg; cannot use it in L." />);
  expect(screen.getByText(/cannot use it in L/)).toBeInTheDocument();
});
