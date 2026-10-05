import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";

const reply = (body, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

function mount(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

test("signed-out visitors are sent to the sign-in form", async () => {
  mount("/products");
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Ingredients" })).not.toBeInTheDocument();
});

test("a wrong password shows the server's message", async () => {
  vi.stubGlobal("fetch", () => reply({ detail: "Incorrect username or password." }, 400));
  mount();
  await userEvent.type(await screen.findByLabelText("Username"), "muthu");
  await userEvent.type(screen.getByLabelText("Password"), "nope");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect username or password.");
});

test("signing in shows the dashboard, and logging out returns to sign in", async () => {
  vi.stubGlobal("fetch", (url) => {
    if (url.includes("/auth/login/")) return reply({ token: "t0k3n", username: "muthu" });
    if (url.includes("/auth/logout/")) return Promise.resolve(new Response(null, { status: 204 }));
    return reply([]);
  });
  mount();
  await userEvent.type(await screen.findByLabelText("Username"), "muthu");
  await userEvent.type(screen.getByLabelText("Password"), "pw-12345-x");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("heading", { name: /what does it cost to make/i })).toBeInTheDocument();
  expect(localStorage.getItem("cc_token")).toBe("t0k3n");

  await userEvent.click(screen.getByRole("button", { name: "Log out" }));
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(localStorage.getItem("cc_token")).toBeNull();
});
