import { useEffect, useState } from 'react';

import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';

const emptyCoupon = {
  code: '',
  type: 'percent',
  value: '10.00',
  min_order_amount: '',
  starts_at: '',
  expires_at: '',
  usage_limit: '',
  is_active: true,
};

export default function AdminCouponsPage() {
  const { token } = useAuth();
  const [coupons, setCoupons] = useState([]);
  const [form, setForm] = useState(emptyCoupon);
  const [error, setError] = useState('');

  async function loadCoupons() {
    try {
      const data = await api.coupons.list(token, { active_only: false, limit: 300 });
      setCoupons(data);
    } catch (err) {
      setError(err.message || 'Failed to load coupons.');
    }
  }

  useEffect(() => {
    loadCoupons();
  }, []);

  async function createCoupon(event) {
    event.preventDefault();
    setError('');

    try {
      await api.coupons.create(token, {
        code: form.code,
        type: form.type,
        value: form.value,
        min_order_amount: form.min_order_amount || null,
        starts_at: form.starts_at || null,
        expires_at: form.expires_at || null,
        usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
        is_active: form.is_active,
      });
      setForm(emptyCoupon);
      await loadCoupons();
    } catch (err) {
      setError(err.message || 'Coupon creation failed.');
    }
  }

  return (
    <section className="stack-gap">
      <div className="section__head">
        <h1>Coupons</h1>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <form className="card" onSubmit={createCoupon}>
        <h3>Create Coupon</h3>

        <div className="grid-three">
          <label>
            Code
            <input value={form.code} onChange={(event) => setForm((prev) => ({ ...prev, code: event.target.value }))} required />
          </label>

          <label>
            Type
            <select value={form.type} onChange={(event) => setForm((prev) => ({ ...prev, type: event.target.value }))}>
              <option value="percent">percent</option>
              <option value="fixed">fixed</option>
            </select>
          </label>

          <label>
            Value
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.value}
              onChange={(event) => setForm((prev) => ({ ...prev, value: event.target.value }))}
              required
            />
          </label>
        </div>

        <div className="grid-three">
          <label>
            Min order amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.min_order_amount}
              onChange={(event) => setForm((prev) => ({ ...prev, min_order_amount: event.target.value }))}
            />
          </label>

          <label>
            Starts at
            <input
              type="datetime-local"
              value={form.starts_at}
              onChange={(event) => setForm((prev) => ({ ...prev, starts_at: event.target.value }))}
            />
          </label>

          <label>
            Expires at
            <input
              type="datetime-local"
              value={form.expires_at}
              onChange={(event) => setForm((prev) => ({ ...prev, expires_at: event.target.value }))}
            />
          </label>
        </div>

        <label>
          Usage limit
          <input
            type="number"
            min="1"
            value={form.usage_limit}
            onChange={(event) => setForm((prev) => ({ ...prev, usage_limit: event.target.value }))}
          />
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => setForm((prev) => ({ ...prev, is_active: event.target.checked }))}
          />
          Active
        </label>

        <button className="btn" type="submit">
          Create Coupon
        </button>
      </form>

      <div className="table-wrap card">
        <table className="table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Type</th>
              <th>Value</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {coupons.map((coupon) => (
              <tr key={coupon.id}>
                <td>{coupon.code}</td>
                <td>{coupon.type}</td>
                <td>{coupon.value}</td>
                <td>{coupon.is_active ? 'yes' : 'no'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
