import { useEffect, useState } from 'react';

import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';

const emptyCategory = {
  name: '',
  slug: '',
  description: '',
  parent_id: null,
  is_active: true,
};

export default function AdminCategoriesPage() {
  const { token } = useAuth();
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState(emptyCategory);
  const [error, setError] = useState('');

  async function loadCategories() {
    try {
      const data = await api.categories.list({ include_inactive: true, limit: 500 });
      setCategories(data);
    } catch (err) {
      setError(err.message || 'Failed to load categories.');
    }
  }

  useEffect(() => {
    loadCategories();
  }, []);

  async function createCategory(event) {
    event.preventDefault();
    setError('');

    try {
      await api.categories.create(token, form);
      setForm(emptyCategory);
      await loadCategories();
    } catch (err) {
      setError(err.message || 'Failed to create category.');
    }
  }

  async function toggleActive(category) {
    try {
      await api.categories.update(token, category.id, { is_active: !category.is_active });
      await loadCategories();
    } catch (err) {
      setError(err.message || 'Failed to update category.');
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Categories</h1>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <form className="card" onSubmit={createCategory}>
        <h3>Create Category</h3>
        <div className="grid-two">
          <label>
            Name
            <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} required />
          </label>
          <label>
            Slug
            <input value={form.slug} onChange={(event) => setForm((prev) => ({ ...prev, slug: event.target.value }))} required />
          </label>
        </div>

        <label>
          Description
          <textarea
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
          />
        </label>

        <button className="btn btn--small" type="submit">
          Add Category
        </button>
      </form>

      <div className="table-wrap card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Slug</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => (
              <tr key={category.id}>
                <td>{category.id}</td>
                <td>{category.name}</td>
                <td>{category.slug}</td>
                <td>{category.is_active ? 'active' : 'inactive'}</td>
                <td>
                  <button className="btn btn--small btn--ghost" onClick={() => toggleActive(category)} type="button">
                    Toggle
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
