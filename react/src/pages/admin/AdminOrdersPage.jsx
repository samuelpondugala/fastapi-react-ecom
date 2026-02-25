import { useState } from 'react';

import StatusPill from '../../components/StatusPill';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format';

export default function AdminOrdersPage() {
  const { token } = useAuth();

  const [orderId, setOrderId] = useState('');
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  async function lookupOrder() {
    setError('');
    setResult(null);

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

  async function payOrder() {
    if (!order) return;

    try {
      const paymentResult = await api.orders.payOrder(token, order.id, {
        provider: 'manual_free',
        apply_tax: true,
        tax_mode: 'percent',
        tax_value: '12.00',
      });
      setResult(paymentResult);
      setOrder(paymentResult.order);
      setError('');
    } catch (err) {
      setError(err.message || 'Could not process payment.');
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Order Center</h1>
        <p className="muted">Lookup any order by ID and process payment using free gateway.</p>
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

          <button className="btn" type="button" onClick={payOrder}>
            Pay with manual_free (12% tax)
          </button>
        </div>
      )}

      {result && (
        <div className="card card--inset">
          <h4>Payment Result</h4>
          <p>
            Status: <StatusPill value={result.payment.status} />
          </p>
          <p className="small muted">Reference: {result.payment.transaction_ref}</p>
        </div>
      )}
    </section>
  );
}
