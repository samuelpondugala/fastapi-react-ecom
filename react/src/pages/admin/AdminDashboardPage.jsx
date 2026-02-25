import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';

export default function AdminDashboardPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState({ users: 0, categories: 0, products: 0, coupons: 0 });
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    async function load() {
      try {
        const [users, categories, products, coupons] = await Promise.all([
          api.users.list(token, { limit: 500 }),
          api.categories.list({ include_inactive: true, limit: 500 }),
          api.products.list({ limit: 500 }),
          api.coupons.list(token, { active_only: false, limit: 500 }),
        ]);

        if (ignore) return;
        setStats({
          users: users.length,
          categories: categories.length,
          products: products.length,
          coupons: coupons.length,
        });
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load dashboard data.');
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [token]);

  return (
    <div className="stack-gap">
      <div className="section__head">
        <h1>Admin Dashboard</h1>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="metric-grid">
        <article className="metric-card">
          <p>Users</p>
          <strong>{stats.users}</strong>
        </article>
        <article className="metric-card">
          <p>Categories</p>
          <strong>{stats.categories}</strong>
        </article>
        <article className="metric-card">
          <p>Products</p>
          <strong>{stats.products}</strong>
        </article>
        <article className="metric-card">
          <p>Coupons</p>
          <strong>{stats.coupons}</strong>
        </article>
      </div>

      <div className="card">
        <h3>Quick Actions</h3>
        <div className="row-gap">
          <Link to="/admin/products" className="btn btn--small">
            Create Product
          </Link>
          <Link to="/admin/categories" className="btn btn--small btn--ghost">
            Manage Categories
          </Link>
          <Link to="/admin/orders" className="btn btn--small btn--ghost">
            Order Payment Center
          </Link>
        </div>
      </div>
    </div>
  );
}
