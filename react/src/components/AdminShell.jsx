import { NavLink, Outlet } from 'react-router-dom';

export default function AdminShell() {
  return (
    <section className="admin-layout fade-in">
      <aside className="admin-sidebar">
        <h2>Admin Panel</h2>
        <p className="muted">Manage users, catalog, coupons, and order payment actions.</p>

        <nav className="admin-nav">
          <NavLink end to="/admin">
            Dashboard
          </NavLink>
          <NavLink to="/admin/users">Users</NavLink>
          <NavLink to="/admin/categories">Categories</NavLink>
          <NavLink to="/admin/products">Products</NavLink>
          <NavLink to="/admin/coupons">Coupons</NavLink>
          <NavLink to="/admin/orders">Order Center</NavLink>
        </nav>
      </aside>

      <section className="admin-content">
        <Outlet />
      </section>
    </section>
  );
}
