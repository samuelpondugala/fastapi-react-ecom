import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import StatusPill from '../../components/StatusPill';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { formatDate, formatMoney, formatPaymentProvider, formatPaymentReference } from '../../lib/format';

const PAGE_SIZE = 10;

export default function AdminOrdersPage() {
  const { token } = useAuth();

  const [page, setPage] = useState(0);
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const offset = page * PAGE_SIZE;
  const startItem = total === 0 ? 0 : offset + 1;
  const endItem = Math.min(total, offset + orders.length);

  useEffect(() => {
    let ignore = false;

    async function loadOrders() {
      setLoading(true);
      setError('');
      try {
        const data = await api.orders.listAdmin(token, {
          limit: PAGE_SIZE,
          offset,
        });
        if (ignore) return;
        setOrders(data.items || []);
        setTotal(Number(data.total || 0));
      } catch (err) {
        if (!ignore) {
          setOrders([]);
          setError(err.message || 'Failed to load admin orders.');
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    loadOrders();
    return () => {
      ignore = true;
    };
  }, [offset, token]);

  useEffect(() => {
    if (page > 0 && page >= totalPages) {
      setPage(totalPages - 1);
    }
  }, [page, totalPages]);

  const pagerLabel = useMemo(() => {
    if (total === 0) return 'No orders yet';
    return `Showing ${startItem}-${endItem} of ${total} orders`;
  }, [endItem, startItem, total]);

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Order Center</h1>
        <p className="muted">Recent orders load 10 at a time with direct access to payment and customer details.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="card">
        <div className="pagination-bar">
          <p className="muted">{pagerLabel}</p>
          <div className="pagination-actions">
            <button type="button" className="btn btn--small btn--ghost" onClick={() => setPage(0)} disabled={page === 0}>
              {'<<'}
            </button>
            <button
              type="button"
              className="btn btn--small btn--ghost"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0}
            >
              {'<'}
            </button>
            <button
              type="button"
              className="btn btn--small btn--ghost"
              onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
              disabled={page >= totalPages - 1 || total === 0}
            >
              {'>'}
            </button>
            <button
              type="button"
              className="btn btn--small btn--ghost"
              onClick={() => setPage(totalPages - 1)}
              disabled={page >= totalPages - 1 || total === 0}
            >
              {'>>'}
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="centered-inline">
          <div className="loader" />
          <span>Loading orders...</span>
        </div>
      )}

      {!loading && orders.length === 0 && <div className="card muted">No orders found.</div>}

      {!loading && orders.length > 0 && (
        <div className="table-wrap card">
          <table className="table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Customer</th>
                <th>Placed</th>
                <th>Total</th>
                <th>Order Status</th>
                <th>Payment</th>
                <th>Reference</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>
                    <strong>#{order.order_number}</strong>
                    <p className="small muted">ID {order.id}</p>
                  </td>
                  <td>
                    <strong>{order.customer_name || 'Customer'}</strong>
                    <p className="small muted">{order.customer_email || `User #${order.user_id}`}</p>
                  </td>
                  <td>{formatDate(order.placed_at)}</td>
                  <td>{formatMoney(order.grand_total)}</td>
                  <td>
                    <StatusPill value={order.status} />
                  </td>
                  <td>
                    <div className="status-stack">
                      <StatusPill value={order.payment_status} />
                      <span className="small muted">{formatPaymentProvider(order.payment_provider)}</span>
                    </div>
                  </td>
                  <td className="small">{formatPaymentReference(order.payment_provider, order.payment_transaction_ref)}</td>
                  <td>
                    <Link className="btn btn--small" to={`/orders/${order.id}`}>
                      View details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
