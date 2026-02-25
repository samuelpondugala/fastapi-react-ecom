import { useEffect, useState } from 'react';

import StatusPill from '../../components/StatusPill';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';

export default function AdminUsersPage() {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedUserError, setSelectedUserError] = useState('');

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
    try {
      const data = await api.users.getById(token, userId);
      setSelectedUser(data);
    } catch (err) {
      setSelectedUser(null);
      setSelectedUserError(err.message || 'Failed to load selected user.');
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Users</h1>
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
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedUserError && <div className="alert alert--error">{selectedUserError}</div>}

      {selectedUser && (
        <article className="card">
          <h3>User Detail (GET /users/:id)</h3>
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
        </article>
      )}
    </section>
  );
}
