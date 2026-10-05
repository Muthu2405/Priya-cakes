import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, tokenStore } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!tokenStore.get());

  // Restore the session if a token is stored.
  useEffect(() => {
    if (!tokenStore.get()) return;
    api.me()
      .then((me) => setUser(me.username))
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  // api.js fires this when the server rejects the token.
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const login = useCallback(async (username, password) => {
    const res = await api.login({ username, password });
    tokenStore.set(res.token);
    setUser(res.username);
  }, []);

  const logout = useCallback(async () => {
    try { await api.logout(); } catch { /* token may already be invalid */ }
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, ready, login, logout }), [user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
