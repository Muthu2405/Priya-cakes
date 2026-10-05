const BASE = import.meta.env.VITE_API_URL ?? "/api";
const TOKEN_KEY = "cc_token";

export class ApiError extends Error {}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// DRF errors come as {field: ["msg"]}, nested lists for rows, or {detail: "msg"}.
function flatten(err, label = "") {
  if (typeof err === "string") return [label ? `${label}: ${err}` : err];
  if (Array.isArray(err)) return err.flatMap((e) => flatten(e, label));
  if (err && typeof err === "object") {
    return Object.entries(err).flatMap(([key, value]) =>
      flatten(value, key === "detail" || key === "non_field_errors" ? label : key.replaceAll("_", " "))
    );
  }
  return [];
}

const authHeader = () => (tokenStore.get() ? { Authorization: `Token ${tokenStore.get()}` } : {});

function expireSession() {
  tokenStore.clear();
  window.dispatchEvent(new Event("auth:expired"));
  return new ApiError("Your session has expired. Sign in again.");
}

async function send(path, { method = "GET", body, params } = {}) {
  const query = new URLSearchParams(
    Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== "")
  ).toString();
  try {
    return await fetch(`${BASE}${path}${query ? `?${query}` : ""}`, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...authHeader() },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.");
  }
}

async function request(path, options) {
  const res = await send(path, options);
  if (res.status === 401) throw expireSession();
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const messages = flatten(data);
    throw new ApiError(messages.join(" ") || `Request failed (${res.status}).`);
  }
  return data;
}

async function download(path, params, failMessage, fallbackName) {
  const res = await send(path, { params });
  if (res.status === 401) throw expireSession();
  if (!res.ok) throw new ApiError(failMessage);
  const blob = await res.blob();
  const name = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const downloadPdf = (id) => download(`/products/${id}/pdf/`, undefined, "Couldn't create the PDF. Try again.", "costing.pdf");
const downloadSalesCsv = (params) => download("/sales/report/csv/", params, "Couldn't create the CSV. Try again.", "sales-report.csv");

export const api = {
  login: (body) => request("/auth/login/", { method: "POST", body }),
  logout: () => request("/auth/logout/", { method: "POST" }),
  me: () => request("/auth/me/"),

  listIngredients: (params) => request("/ingredients/", { params }),
  createIngredient: (body) => request("/ingredients/", { method: "POST", body }),
  updateIngredient: (id, body) => request(`/ingredients/${id}/`, { method: "PUT", body }),
  deleteIngredient: (id) => request(`/ingredients/${id}/`, { method: "DELETE" }),

  listProducts: (params) => request("/products/", { params }),
  getProduct: (id) => request(`/products/${id}/`),
  createProduct: (body) => request("/products/", { method: "POST", body }),
  updateProduct: (id, body) => request(`/products/${id}/`, { method: "PUT", body }),
  deleteProduct: (id) => request(`/products/${id}/`, { method: "DELETE" }),
  calculate: (body) => request("/products/calculate/", { method: "POST", body }),
  downloadPdf,

  listSales: (params) => request("/sales/", { params }),
  createSale: (body) => request("/sales/", { method: "POST", body }),
  updateSale: (id, body) => request(`/sales/${id}/`, { method: "PUT", body }),
  deleteSale: (id) => request(`/sales/${id}/`, { method: "DELETE" }),
  salesReport: (params) => request("/sales/report/", { params }),
  downloadSalesCsv,
};
