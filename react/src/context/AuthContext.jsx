import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { api } from '../lib/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'ecom_token';
const USER_KEY = 'ecom_user';

function loadStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function loadStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(loadStoredToken());
  const [user, setUser] = useState(loadStoredUser());
  const [loading, setLoading] = useState(Boolean(loadStoredToken()));

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function hydrateUser() {
      try {
        const me = await api.auth.me(token);
        if (cancelled) return;
        setUser(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
      } catch {
        if (cancelled) return;
        setToken(null);
        setUser(null);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    hydrateUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token),
      isAdmin: user?.role === 'admin',
      isVendor: user?.role === 'vendor',
      async login(identifier, password) {
        const identity = (identifier || '').trim();
        const loginPayload = { password };
        if (identity.includes('@')) {
          loginPayload.email = identity;
        } else {
          loginPayload.username = identity;
        }
        const result = await api.auth.login(loginPayload);
        setToken(result.access_token);
        localStorage.setItem(TOKEN_KEY, result.access_token);
        const me = await api.auth.me(result.access_token);
        setUser(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
        return me;
      },
      async register(payload) {
        return api.auth.register(payload);
      },
      async refreshMe() {
        if (!token) return null;
        const me = await api.auth.me(token);
        setUser(me);
        localStorage.setItem(USER_KEY, JSON.stringify(me));
        return me;
      },
      logout() {
        setToken(null);
        setUser(null);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      },
    }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
