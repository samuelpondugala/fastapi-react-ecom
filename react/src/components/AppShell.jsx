import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { TOAST_EVENT } from '../lib/toast';

const THEME_KEY = 'ecom_theme_mode';

function getInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') {
    return saved;
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function AppShell() {
  const { isAuthenticated, isAdmin, isVendor, user, logout } = useAuth();
  const [theme, setTheme] = useState(getInitialTheme);
  const [toasts, setToasts] = useState([]);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    const timers = new Map();

    function onToast(event) {
      const toast = event.detail;
      if (!toast?.id || !toast?.message) return;

      setToasts((prev) => [...prev, toast]);
      const timeout = window.setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== toast.id));
        timers.delete(toast.id);
      }, Math.max(3000, Number(toast.duration) || 4200));
      timers.set(toast.id, timeout);
    }

    window.addEventListener(TOAST_EVENT, onToast);
    return () => {
      window.removeEventListener(TOAST_EVENT, onToast);
      timers.forEach((timer) => window.clearTimeout(timer));
      timers.clear();
    };
  }, []);

  function dismissToast(toastId) {
    setToasts((prev) => prev.filter((item) => item.id !== toastId));
  }

  return (
    <div className="app-bg">
      <header className="topbar">
        <div className="wrap topbar__inner">
          <NavLink to="/" className="brand">
            <span className="brand__kicker">DigiKart</span>
            <span className="brand__title">Modern Commerce Studio</span>
          </NavLink>

          <nav className="navlinks" aria-label="Main navigation">
            <NavLink to="/catalog">Catalog</NavLink>
            {isAuthenticated && <NavLink to="/cart">Cart</NavLink>}
            {isAuthenticated && <NavLink to="/orders">Orders</NavLink>}
            {isAuthenticated && <NavLink to="/profile">Profile</NavLink>}
            {(isVendor || isAdmin) && <NavLink to="/vendor/products">Vendor</NavLink>}
            {isAdmin && <NavLink to="/admin">Admin</NavLink>}
          </nav>

          <div className="topbar__actions">
            <button
              type="button"
              className="btn btn--small btn--ghost theme-toggle"
              onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
            >
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
            {!isAuthenticated ? (
              <>
                <NavLink to="/login" className="btn btn--ghost btn--small">
                  Login
                </NavLink>
                <NavLink to="/register" className="btn btn--small">
                  Register
                </NavLink>
              </>
            ) : (
              <>
                <span className="chip">{user?.email}</span>
                <button type="button" className="btn btn--small btn--danger" onClick={logout}>
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main key={location.pathname} className="wrap page fade-in">
        <Outlet />
      </main>

      <div className="toast-stack" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast-global ${
              toast.type === 'error' ? 'toast-global--error' : toast.type === 'success' ? 'toast-global--success' : ''
            }`}
            role="status"
          >
            <span>{toast.message}</span>
            <button type="button" className="toast-global__close" onClick={() => dismissToast(toast.id)}>
              x
            </button>
          </div>
        ))}
      </div>

      <footer className="footer">
        <div className="wrap footer__inner">
          <p>Built with React + Vite for your FastAPI commerce backend.</p>
          <p>Route-aware UI, customer storefront, and admin operations panel.</p>
        </div>
      </footer>
    </div>
  );
}
