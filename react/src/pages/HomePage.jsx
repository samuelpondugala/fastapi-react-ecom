import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import ProductCard from '../components/ProductCard';
import StatusPill from '../components/StatusPill';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { errorToast, successToast } from '../lib/toast';

export default function HomePage() {
  const { token } = useAuth();
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [apiStatus, setApiStatus] = useState({ health: 'unknown', ready: 'unknown' });
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;

    async function load() {
      const [categoryData, productData, healthData, readyData] = await Promise.allSettled([
        api.categories.list({ include_inactive: false, limit: 12 }),
        api.products.list({ status_filter: 'active', limit: 6 }),
        api.health.status(),
        api.health.ready(),
      ]);

      if (ignore) return;

      if (categoryData.status === 'fulfilled') {
        setCategories(categoryData.value);
      } else {
        setError(categoryData.reason?.message || 'Failed to load homepage data.');
      }

      if (productData.status === 'fulfilled') {
        setProducts(productData.value);
      } else {
        setError(productData.reason?.message || 'Failed to load homepage data.');
      }

      setApiStatus({
        health: healthData.status === 'fulfilled' ? healthData.value.status : 'down',
        ready: readyData.status === 'fulfilled' ? readyData.value.status : 'down',
      });
    }

    load();
    return () => {
      ignore = true;
    };
  }, []);

  async function addToCart(variant) {
    if (!variant) {
      setError('This product variant is not available.');
      errorToast('This product variant is not available.');
      return;
    }
    if (!token) {
      setError('Please login to add items to cart.');
      errorToast('Please login to add items to cart.');
      return;
    }
    try {
      await api.cart.addItem(token, { variant_id: variant.id, quantity: 1 });
      setError('');
      successToast('Item added to cart.');
    } catch (err) {
      setError(err.message || 'Could not add item to cart.');
    }
  }

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">FastAPI + React + Admin</p>
          <h1>Commerce frontend with seamless routing and full API coverage.</h1>
          <p className="muted">
            Browse products, checkout with free payment gateways, apply tax only during payment, and manage
            operations in the integrated admin control room.
          </p>

          <div className="hero__actions">
            <Link className="btn" to="/catalog">
              Explore Catalog
            </Link>
            <Link className="btn btn--ghost" to="/admin">
              Open Admin
            </Link>
          </div>
        </div>

        <div className="hero__card">
          <h3>Backend Routes Connected</h3>
          <ul>
            <li>Auth + profile + addresses</li>
            <li>Catalog + variants + reviews</li>
            <li>Cart + checkout + order tracking</li>
            <li>Payment quote + pay with free gateways</li>
            <li>Admin users/categories/products/coupons/order center</li>
          </ul>
          <div className="status-row">
            <span>Health</span>
            <StatusPill value={apiStatus.health} />
          </div>
          <div className="status-row">
            <span>Readiness</span>
            <StatusPill value={apiStatus.ready} />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section__head">
          <h2>Popular Categories</h2>
        </div>
        <div className="chip-list">
          {categories.map((category) => (
            <Link key={category.id} className="chip chip--link" to={`/catalog?category=${category.id}`}>
              {category.name}
            </Link>
          ))}
          {categories.length === 0 && <p className="muted">No categories yet.</p>}
        </div>
      </section>

      <section className="section">
        <div className="section__head">
          <h2>Featured Products</h2>
          <Link to="/catalog" className="inline-link">
            View all
          </Link>
        </div>

        {error && <div className="alert alert--error">{error}</div>}

        <div className="product-grid">
          {products.map((product, index) => (
            <div key={product.id} className="stagger" style={{ animationDelay: `${index * 70}ms` }}>
              <ProductCard product={product} onAddToCart={addToCart} />
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
