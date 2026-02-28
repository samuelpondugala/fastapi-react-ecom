import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import ProductCard from '../components/ProductCard';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { errorToast, successToast } from '../lib/toast';

export default function CatalogPage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedCategory = searchParams.get('category') || '';
  const searchText = searchParams.get('q') || '';

  const filters = useMemo(
    () => ({
      category_id: selectedCategory || undefined,
      q: searchText || undefined,
      status_filter: 'active',
      limit: 120,
    }),
    [selectedCategory, searchText],
  );

  useEffect(() => {
    let ignore = false;
    async function loadCategories() {
      try {
        const data = await api.categories.list({ include_inactive: false, limit: 200 });
        if (!ignore) setCategories(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load categories.');
      }
    }

    loadCategories();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;
    async function loadProducts() {
      setLoading(true);
      setError('');
      try {
        const data = await api.products.list(filters);
        if (!ignore) setProducts(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load products.');
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    loadProducts();
    return () => {
      ignore = true;
    };
  }, [filters]);

  async function addToCart(variant) {
    if (!token) {
      setError('Please login to add products to cart.');
      errorToast('Please login to add products to cart.');
      return;
    }
    try {
      await api.cart.addItem(token, { variant_id: variant.id, quantity: 1 });
      setError('');
      successToast('Item added to cart.');
    } catch (err) {
      setError(err.message || 'Failed to add item to cart.');
    }
  }

  function onSearchSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const q = form.get('q')?.toString() || '';
    const category = form.get('category')?.toString() || '';

    const next = {};
    if (q) next.q = q;
    if (category) next.category = category;
    setSearchParams(next);
  }

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>Catalog</h1>
        <p className="muted">Filter products and add any active variant directly to cart.</p>
      </div>

      <form className="toolbar" onSubmit={onSearchSubmit}>
        <input name="q" type="search" placeholder="Search by name..." defaultValue={searchText} />
        <select name="category" defaultValue={selectedCategory}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <button className="btn btn--small" type="submit">
          Apply
        </button>
      </form>

      {error && <div className="alert alert--error">{error}</div>}
      {loading && (
        <div className="centered-inline">
          <div className="loader" />
          <span>Loading products...</span>
        </div>
      )}

      {!loading && products.length === 0 && <div className="card muted">No products match your filters.</div>}

      <div className="product-grid">
        {products.map((product, index) => (
          <div key={product.id} className="stagger" style={{ animationDelay: `${index * 45}ms` }}>
            <ProductCard product={product} onAddToCart={addToCart} />
          </div>
        ))}
      </div>
    </section>
  );
}
