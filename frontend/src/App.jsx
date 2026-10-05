import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Ingredients from "./pages/Ingredients.jsx";
import Login from "./pages/Login.jsx";
import Products from "./pages/Products.jsx";
import ProductCreate from "./pages/ProductCreate.jsx";
import ProductDetails from "./pages/ProductDetails.jsx";
import Sales from "./pages/Sales.jsx";
import SalesReport from "./pages/SalesReport.jsx";

function RequireAuth() {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

export default function App() {
  const { user, logout } = useAuth();
  return (
    <>
      {user && (
        <header className="topbar">
          <NavLink to="/" className="brand">Cost Calculator</NavLink>
          <nav aria-label="Main">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/ingredients">Ingredients</NavLink>
            <NavLink to="/products">Products</NavLink>
            <NavLink to="/sales" end>Sales</NavLink>
            <NavLink to="/sales/report">Sales report</NavLink>
          </nav>
          <div className="account">
            <span>{user}</span>
            <button type="button" onClick={logout}>Log out</button>
          </div>
        </header>
      )}
      <main className="page">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ingredients" element={<Ingredients />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/new" element={<ProductCreate />} />
            <Route path="/products/:id" element={<ProductDetails />} />
            <Route path="/products/:id/edit" element={<ProductCreate />} />
            <Route path="/sales" element={<Sales />} />
            <Route path="/sales/report" element={<SalesReport />} />
          </Route>
          <Route path="*" element={<p>That page doesn't exist.</p>} />
        </Routes>
      </main>
    </>
  );
}
