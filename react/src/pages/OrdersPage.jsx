import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import StatusPill from '../components/StatusPill';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { formatDate, formatMoney, formatPaymentProvider, formatPaymentReference } from '../lib/format';

export default function OrdersPage() {
  const { token } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;
    async function loadOrders() {
      setLoading(true);
      try {
        const data = await api.orders.listMine(token, { limit: 100 });
        if (!ignore) setOrders(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load orders.');
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    loadOrders();
    return () => {
      ignore = true;
    };
  }, [token]);

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>My Orders</h1>
      </div>

      {error && <div className="alert alert--error">{error}</div>}
      {loading && (
        <div className="centered-inline">
          <div className="loader" />
          <span>Loading orders...</span>
        </div>
      )}

      {!loading && orders.length === 0 && <div className="card muted">No orders yet.</div>}

      <div className="card-list">
        {orders.map((order) => (
          <article className="card order-card" key={order.id}>
            <div>
              <p className="eyebrow">#{order.order_number}</p>
              <h3>Order {order.id}</h3>
              <p className="muted">Placed: {formatDate(order.placed_at)}</p>
            </div>

            <div className="order-card__items">
              {order.items.slice(0, 3).map((item) => {
                const title = item.product_name_snapshot || `Variant #${item.variant_id}`;
                const image = item.product_image_url ? (
                  <img src={item.product_image_url} alt={item.product_image_alt || title} loading="lazy" />
                ) : (
                  <div className="image-placeholder">No image</div>
                );
                return item.product_id ? (
                  <Link
                    key={item.id}
                    to={`/products/${item.product_id}`}
                    className="order-card__thumb"
                    title={title}
                    aria-label={`View ${title}`}
                  >
                    {image}
                  </Link>
                ) : (
                  <div key={item.id} className="order-card__thumb" title={title}>
                    {image}
                  </div>
                );
              })}
              {order.items.length > 3 && <span className="chip">+{order.items.length - 3} more</span>}
            </div>

            <div className="order-card__meta">
              <StatusPill value={order.status} />
              <StatusPill value={order.payment_status} />
              <span className="small muted">
                {formatPaymentProvider(order.payment_provider)} •{' '}
                {formatPaymentReference(order.payment_provider, order.payment_transaction_ref)}
              </span>
              <strong>{formatMoney(order.grand_total)}</strong>
            </div>

            <Link className="btn btn--small" to={`/orders/${order.id}`}>
              View / Pay
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
