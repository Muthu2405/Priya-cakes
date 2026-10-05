import { ApiError, api, tokenStore } from "../services/api.js";

const reply = (body, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

test("turns DRF validation errors into one readable message", async () => {
  vi.stubGlobal("fetch", () => reply({ ingredients: ["Flour is priced in kg (weight); cannot use it in L (volume)."] }, 400));
  await expect(api.calculate({})).rejects.toThrow(/cannot use it in L/);
});

test("sends the saved token", async () => {
  tokenStore.set("abc123");
  const fetchMock = vi.fn(() => reply([]));
  vi.stubGlobal("fetch", fetchMock);
  await api.listIngredients();
  expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Token abc123");
});

test("a 401 clears the token and announces the expired session", async () => {
  tokenStore.set("stale");
  const expired = vi.fn();
  window.addEventListener("auth:expired", expired);
  vi.stubGlobal("fetch", () => reply({ detail: "Invalid token." }, 401));
  await expect(api.listProducts()).rejects.toBeInstanceOf(ApiError);
  expect(tokenStore.get()).toBeNull();
  expect(expired).toHaveBeenCalled();
  window.removeEventListener("auth:expired", expired);
});

test("explains when the server can't be reached", async () => {
  vi.stubGlobal("fetch", () => Promise.reject(new TypeError("fetch failed")));
  await expect(api.listProducts()).rejects.toThrow(/Can't reach the server/);
});
