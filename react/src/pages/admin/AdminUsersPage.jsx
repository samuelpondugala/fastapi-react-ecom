import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import StatusPill from '../../components/StatusPill';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { formatDate, formatMoney, formatPaymentProvider, formatPaymentReference } from '../../lib/format';

export default function AdminUsersPage() {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedUserOrders, setSelectedUserOrders] = useState([]);
  const [selectedUserError, setSelectedUserError] = useState('');
  const [loadingOrders, setLoadingOrders] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadUsers() {
      try {
        const data = await api.users.list(token, { limit: 200 });
        if (!ignore) setUsers(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Failed to load users.');
      }
    }

    loadUsers();
    return () => {
      ignore = true;
    };
  }, [token]);

  async function inspectUser(userId) {
    setSelectedUserError('');
    setLoadingOrders(true);
    try {
      const [userData, orderData] = await Promise.all([
        api.users.getById(token, userId),
        api.users.listOrders(token, userId, { limit: 200 }),
      ]);
      setSelectedUser(userData);
      setSelectedUserOrders(orderData);
    } catch (err) {
      setSelectedUser(null);
      setSelectedUserOrders([]);
      setSelectedUserError(err.message || 'Failed to load selected user.');
    } finally {
      setLoadingOrders(false);
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Users</h1>
        <p className="muted">Inspect a user to review profile details and every order they have placed.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="table-wrap card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>{user.full_name || '--'}</td>
                <td>{user.role}</td>
                <td>
                  <StatusPill value={user.is_active ? 'active' : 'inactive'} />
                </td>
                <td>
                  <button className="btn btn--small btn--ghost" type="button" onClick={() => inspectUser(user.id)}>
                    View user
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedUserError && <div className="alert alert--error">{selectedUserError}</div>}

      {selectedUser && (
        <article className="card stack-gap">
          <div>
            <h3>User Detail</h3>
            <div className="grid-two">
              <p>
                <strong>ID:</strong> {selectedUser.id}
              </p>
              <p>
                <strong>Email:</strong> {selectedUser.email}
              </p>
              <p>
                <strong>Name:</strong> {selectedUser.full_name || '--'}
              </p>
              <p>
                <strong>Phone:</strong> {selectedUser.phone || '--'}
              </p>
              <p>
                <strong>Role:</strong> {selectedUser.role}
              </p>
              <p>
                <strong>Active:</strong> {selectedUser.is_active ? 'yes' : 'no'}
              </p>
            </div>
          </div>

          <div className="stack-gap">
            <div className="section__head section__head--compact">
              <h3>User Orders</h3>
              <p className="muted">{loadingOrders ? 'Loading orders...' : `${selectedUserOrders.length} orders found`}</p>
            </div>

            {loadingOrders && (
              <div className="centered-inline">
                <div className="loader" />
                <span>Loading user orders...</span>
              </div>
            )}

            {!loadingOrders && selectedUserOrders.length === 0 && <div className="card card--inset muted">No orders yet.</div>}

            {!loadingOrders && selectedUserOrders.length > 0 && (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Placed</th>
                      <th>Total</th>
                      <th>Order Status</th>
                      <th>Payment</th>
                      <th>Reference</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {selectedUserOrders.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <strong>#{order.order_number}</strong>
                          <p className="small muted">ID {order.id}</p>
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
                        <td>{formatPaymentReference(order.payment_provider, order.payment_transaction_ref)}</td>
                        <td>
                          <Link className="btn btn--small" to={`/orders/${order.id}`}>
                            Open
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </article>
      )}
    </section>
  );
}
