import { useState } from 'react';
import { Link } from 'react-router-dom';

import StatusPill from '../../components/StatusPill';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format';

export default function AdminOrdersPage() {
  const { token } = useAuth();

  const [orderId, setOrderId] = useState('');
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  async function lookupOrder() {
    setError('');

    if (!orderId) {
      setError('Enter an order ID first.');
      return;
    }

    try {
      const data = await api.orders.getById(token, orderId);
      setOrder(data);
    } catch (err) {
      setError(err.message || 'Could not find order.');
      setOrder(null);
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Order Center</h1>
        <p className="muted">Lookup any order by ID and open Razorpay payment screen.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="card">
        <div className="row-gap">
          <input
            value={orderId}
            onChange={(event) => setOrderId(event.target.value)}
            placeholder="Enter order id (e.g. 12)"
          />
          <button type="button" className="btn btn--small" onClick={lookupOrder}>
            Lookup
          </button>
        </div>
      </div>

      {order && (
        <div className="card">
          <h3>Order #{order.order_number}</h3>
          <p>
            Status: <StatusPill value={order.status} />
          </p>
          <p>
            Payment: <StatusPill value={order.payment_status} />
          </p>
          <p>
            Grand total: <strong>{formatMoney(order.grand_total)}</strong>
          </p>

          <Link className="btn" to={`/orders/${order.id}?provider=razorpay_upi`}>
            Open payment page
          </Link>
        </div>
      )}
    </section>
  );
}
