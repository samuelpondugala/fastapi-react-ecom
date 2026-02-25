import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

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
  const location = useLocation();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return (
    <div className="app-bg">
      <header className="topbar">
        <div className="wrap topbar__inner">
          <NavLink to="/" className="brand">
            <span className="brand__kicker">Mirafra</span>
            <span className="brand__title">Commerce Studio</span>
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

      <footer className="footer">
        <div className="wrap footer__inner">
          <p>Built with React + Vite for your FastAPI commerce backend.</p>
          <p>Route-aware UI, customer storefront, and admin operations panel.</p>
        </div>
      </footer>
    </div>
  );
}
