import { useEffect, useState } from 'react';

import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format';

const emptyForm = {
  category_id: '',
  name: '',
  slug: '',
  description: '',
  brand: '',
  status: 'active',
  image_url: '',
  sku: '',
  price: '0.00',
  compare_at_price: '',
  weight: '',
};

const sampleImportTemplate = `{
  "products": [
    {
      "title": "Wireless Mouse Pro",
      "description": "Ergonomic mouse with silent clicks",
      "category": "electronics",
      "price": 29.99,
      "discountPercentage": 10,
      "brand": "LogiTech",
      "sku": "MOU-LOGI-001",
      "weight": 0.12,
      "stock": 100,
      "images": [
        "https://example.com/mouse-1.jpg"
      ],
      "thumbnail": "https://example.com/mouse-thumb.jpg"
    }
  ]
}`;

export default function AdminProductsPage({ vendorMode = false }) {
  const { token } = useAuth();
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [importLimit, setImportLimit] = useState(20);
  const [importSkip, setImportSkip] = useState(0);
  const [importUpdateExisting, setImportUpdateExisting] = useState(false);
  const [importCategory, setImportCategory] = useState('Imported');
  const [jsonPayload, setJsonPayload] = useState(sampleImportTemplate);
  const [importResult, setImportResult] = useState(null);
  const [importing, setImporting] = useState(false);

  async function loadData() {
    try {
      const [categoryData, productData] = await Promise.all([
        api.categories.list({ include_inactive: true, limit: 300 }),
        api.products.list({ limit: 300 }),
      ]);
      setCategories(categoryData);
      setProducts(productData);
    } catch (err) {
      setError(err.message || 'Failed to load products page data.');
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function createProduct(event) {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      await api.products.create(token, {
        category_id: Number(form.category_id),
        name: form.name,
        slug: form.slug,
        description: form.description,
        brand: form.brand,
        status: form.status,
        images: form.image_url
          ? [
              {
                image_url: form.image_url,
                alt_text: form.name,
                sort_order: 0,
                is_primary: true,
              },
            ]
          : [],
        variants: [
          {
            sku: form.sku,
            attributes_json: { source: 'admin-form' },
            price: form.price,
            compare_at_price: form.compare_at_price || null,
            currency: 'INR',
            weight: form.weight || null,
            is_active: true,
          },
        ],
      });

      setForm(emptyForm);
      await loadData();
      setMessage('Product created successfully.');
    } catch (err) {
      setError(err.message || 'Product creation failed.');
    }
  }

  async function updateStatus(productId, status) {
    try {
      await api.products.update(token, productId, { status });
      await loadData();
      setMessage('Product status updated.');
    } catch (err) {
      setError(err.message || 'Product status update failed.');
    }
  }

  async function importFromDummyJson() {
    setError('');
    setMessage('');
    setImportResult(null);
    setImporting(true);

    try {
      const result = await api.products.importDummyJson(token, {
        limit: Number(importLimit),
        skip: Number(importSkip),
        update_existing: importUpdateExisting,
        default_category_name: importCategory || 'Imported',
      });
      setImportResult(result);
      await loadData();
      setMessage('DummyJSON import completed.');
    } catch (err) {
      setError(err.message || 'DummyJSON import failed.');
    } finally {
      setImporting(false);
    }
  }

  async function importFromJson(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    setImportResult(null);
    setImporting(true);

    try {
      const parsed = JSON.parse(jsonPayload);
      const products = Array.isArray(parsed) ? parsed : parsed?.products;
      if (!Array.isArray(products)) {
        throw new Error('JSON must be either a product array or an object with a "products" array');
      }

      const result = await api.products.importFromJson(token, {
        products,
        update_existing: importUpdateExisting,
        default_category_name: importCategory || 'Imported',
      });
      setImportResult(result);
      await loadData();
      setMessage('JSON import completed.');
    } catch (err) {
      setError(err.message || 'JSON import failed.');
    } finally {
      setImporting(false);
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>{vendorMode ? 'Vendor Product Studio' : 'Products'}</h1>
        <p className="muted">
          {vendorMode
            ? 'Create and import products in bulk as a vendor.'
            : 'Create, import, and manage catalog products.'}
        </p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}
      {message && <div className="alert alert--success">{message}</div>}

      <div className="card stack-gap">
        <h3>Bulk Import (DummyJSON or Manual JSON)</h3>
        <div className="grid-three">
          <label>
            DummyJSON limit
            <input
              type="number"
              min="1"
              max="100"
              value={importLimit}
              onChange={(event) => setImportLimit(event.target.value)}
            />
          </label>
          <label>
            DummyJSON skip
            <input type="number" min="0" value={importSkip} onChange={(event) => setImportSkip(event.target.value)} />
          </label>
          <label>
            Default category
            <input value={importCategory} onChange={(event) => setImportCategory(event.target.value)} />
          </label>
        </div>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={importUpdateExisting}
            onChange={(event) => setImportUpdateExisting(event.target.checked)}
          />
          Update existing products if SKU/slug already exists
        </label>

        <div className="row-gap">
          <button type="button" className="btn btn--small" onClick={importFromDummyJson} disabled={importing}>
            {importing ? 'Importing...' : 'Import from dummyjson.com'}
          </button>
        </div>

        <form className="stack-gap" onSubmit={importFromJson}>
          <label>
            Paste JSON payload
            <textarea
              rows="14"
              value={jsonPayload}
              onChange={(event) => setJsonPayload(event.target.value)}
              placeholder='{"products":[...]}'
            />
          </label>
          <button type="submit" className="btn btn--ghost btn--small" disabled={importing}>
            {importing ? 'Importing...' : 'Import pasted JSON'}
          </button>
        </form>

        {importResult && (
          <div className="card card--inset">
            <h4>Import Result</h4>
            <div className="grid-two">
              <p>
                <strong>Source:</strong> {importResult.source}
              </p>
              <p>
                <strong>Total input:</strong> {importResult.total_input}
              </p>
              <p>
                <strong>Created products:</strong> {importResult.created_products}
              </p>
              <p>
                <strong>Updated products:</strong> {importResult.updated_products}
              </p>
              <p>
                <strong>Skipped products:</strong> {importResult.skipped_products}
              </p>
              <p>
                <strong>Created categories:</strong> {importResult.created_categories}
              </p>
            </div>
            {importResult.errors?.length > 0 && (
              <>
                <p className="small muted">Errors</p>
                <ul className="list-clean">
                  {importResult.errors.map((item, index) => (
                    <li key={`${item}-${index}`} className="small">
                      {item}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>

      <form className="card" onSubmit={createProduct}>
        <h3>Create Product</h3>

        <div className="grid-two">
          <label>
            Category
            <select
              required
              value={form.category_id}
              onChange={(event) => setForm((prev) => ({ ...prev, category_id: event.target.value }))}
            >
              <option value="">Select category</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Status
            <select value={form.status} onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}>
              <option value="active">active</option>
              <option value="draft">draft</option>
              <option value="archived">archived</option>
            </select>
          </label>
        </div>

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

        <div className="grid-two">
          <label>
            Brand
            <input value={form.brand} onChange={(event) => setForm((prev) => ({ ...prev, brand: event.target.value }))} />
          </label>
          <label>
            Image URL
            <input value={form.image_url} onChange={(event) => setForm((prev) => ({ ...prev, image_url: event.target.value }))} />
          </label>
        </div>

        <div className="grid-three">
          <label>
            SKU
            <input value={form.sku} onChange={(event) => setForm((prev) => ({ ...prev, sku: event.target.value }))} required />
          </label>
          <label>
            Price
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.price}
              onChange={(event) => setForm((prev) => ({ ...prev, price: event.target.value }))}
              required
            />
          </label>
          <label>
            Compare at
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.compare_at_price}
              onChange={(event) => setForm((prev) => ({ ...prev, compare_at_price: event.target.value }))}
            />
          </label>
        </div>

        <button className="btn" type="submit">
          Create Product
        </button>
      </form>

      <div className="table-wrap card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Status</th>
              <th>Price</th>
              <th>{vendorMode ? 'Status' : 'Update status'}</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => {
              const variant = product.variants?.[0];
              return (
                <tr key={product.id}>
                  <td>{product.id}</td>
                  <td>{product.name}</td>
                  <td>{product.status}</td>
                  <td>{variant ? formatMoney(variant.price, variant.currency) : '--'}</td>
                  <td>
                    <select
                      value={product.status}
                      onChange={(event) => updateStatus(product.id, event.target.value)}
                    >
                      <option value="active">active</option>
                      <option value="draft">draft</option>
                      <option value="archived">archived</option>
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
