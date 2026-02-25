import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { formatMoney } from '../lib/format';

const emptyAddress = {
  label: '',
  line1: '',
  line2: '',
  city: '',
  state: '',
  postal_code: '',
  country: 'IND',
  is_default: false,
};

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [cart, setCart] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [shippingAddressId, setShippingAddressId] = useState('');
  const [billingAddressId, setBillingAddressId] = useState('');
  const [shippingTotal, setShippingTotal] = useState('5.00');
  const [newAddress, setNewAddress] = useState(emptyAddress);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function loadData() {
    setLoading(true);
    try {
      const [cartData, addressData] = await Promise.all([api.cart.getMine(token), api.addresses.listMine(token)]);
      setCart(cartData);
      setAddresses(addressData);

      const preferred = addressData.find((item) => item.is_default) || addressData[0];
      if (preferred) {
        setShippingAddressId(String(preferred.id));
        setBillingAddressId(String(preferred.id));
      }
    } catch (err) {
      setError(err.message || 'Failed to load checkout information.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const subtotal = useMemo(() => {
    const items = cart?.items || [];
    return items.reduce((sum, item) => sum + Number(item.unit_price) * Number(item.quantity), 0);
  }, [cart]);

  function renderItemIdentity(item) {
    const name = item.product_name || `Variant #${item.variant_id}`;
    const imageAlt = item.product_image_alt || name;
    const image = item.product_image_url ? (
      <img src={item.product_image_url} alt={imageAlt} loading="lazy" />
    ) : (
      <div className="image-placeholder">No image</div>
    );

    return (
      <div className="line-item line-item--compact">
        {item.product_id ? (
          <Link to={`/products/${item.product_id}`} className="line-item__media" aria-label={`View ${name}`}>
            {image}
          </Link>
        ) : (
          <div className="line-item__media">{image}</div>
        )}

        <div className="line-item__meta">
          {item.product_id ? (
            <Link to={`/products/${item.product_id}`} className="line-item__name">
              {name}
            </Link>
          ) : (
            <p className="line-item__name">{name}</p>
          )}
          <p className="small muted">SKU: {item.variant_sku || item.variant_id}</p>
        </div>
      </div>
    );
  }

  async function createAddress(event) {
    event.preventDefault();
    setError('');

    try {
      await api.addresses.createMine(token, { ...newAddress });
      setNewAddress(emptyAddress);
      await loadData();
    } catch (err) {
      setError(err.message || 'Could not create address.');
    }
  }

  async function submitCheckout(event) {
    event.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const order = await api.orders.checkout(token, {
        shipping_address_id: shippingAddressId ? Number(shippingAddressId) : null,
        billing_address_id: billingAddressId ? Number(billingAddressId) : null,
        shipping_total: shippingTotal || '0.00',
        tax_total: '0.00',
      });
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err.message || 'Checkout failed.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="centered-screen">
        <div className="loader" />
        <p>Loading checkout...</p>
      </div>
    );
  }

  if ((cart?.items || []).length === 0) {
    return (
      <section className="section fade-in">
        <h1>Checkout</h1>
        <div className="card muted">Your cart is empty. Add items before checkout.</div>
      </section>
    );
  }

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>Checkout</h1>
        <p className="muted">Taxes are charged only when payment is processed on order detail page.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="split-grid">
        <form className="card" onSubmit={submitCheckout}>
          <h3>Delivery & Billing</h3>

          <label>
            Shipping address
            <select value={shippingAddressId} onChange={(event) => setShippingAddressId(event.target.value)}>
              <option value="">No address selected</option>
              {addresses.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label || `Address ${item.id}`} - {item.city}, {item.country}
                </option>
              ))}
            </select>
          </label>

          <label>
            Billing address
            <select value={billingAddressId} onChange={(event) => setBillingAddressId(event.target.value)}>
              <option value="">No address selected</option>
              {addresses.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label || `Address ${item.id}`} - {item.city}, {item.country}
                </option>
              ))}
            </select>
          </label>

          <label>
            Shipping fee
            <input
              type="number"
              min="0"
              step="0.01"
              value={shippingTotal}
              onChange={(event) => setShippingTotal(event.target.value)}
            />
          </label>

          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? 'Creating order...' : 'Create order'}
          </button>
        </form>

        <div className="stack-gap">
          <div className="card">
            <h3>Items in this order</h3>
            <ul className="list-clean">
              {cart.items.map((item) => (
                <li key={item.id} className="checkout-item-row">
                  {renderItemIdentity(item)}
                  <p className="small">
                    {item.quantity} x {formatMoney(item.unit_price)} ={' '}
                    <strong>{formatMoney(Number(item.unit_price) * Number(item.quantity))}</strong>
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <form className="card" onSubmit={createAddress}>
            <h3>Add address</h3>

            <div className="grid-two">
              <label>
                Label
                <input
                  value={newAddress.label}
                  onChange={(event) => setNewAddress((prev) => ({ ...prev, label: event.target.value }))}
                />
              </label>

              <label>
                Country
                <input
                  value={newAddress.country}
                  onChange={(event) => setNewAddress((prev) => ({ ...prev, country: event.target.value }))}
                  required
                />
              </label>
            </div>

            <label>
              Line 1
              <input
                value={newAddress.line1}
                onChange={(event) => setNewAddress((prev) => ({ ...prev, line1: event.target.value }))}
                required
              />
            </label>

            <label>
              Line 2
              <input
                value={newAddress.line2}
                onChange={(event) => setNewAddress((prev) => ({ ...prev, line2: event.target.value }))}
              />
            </label>

            <div className="grid-two">
              <label>
                City
                <input
                  value={newAddress.city}
                  onChange={(event) => setNewAddress((prev) => ({ ...prev, city: event.target.value }))}
                  required
                />
              </label>

              <label>
                State
                <input
                  value={newAddress.state}
                  onChange={(event) => setNewAddress((prev) => ({ ...prev, state: event.target.value }))}
                  required
                />
              </label>
            </div>

            <label>
              Postal code
              <input
                value={newAddress.postal_code}
                onChange={(event) => setNewAddress((prev) => ({ ...prev, postal_code: event.target.value }))}
                required
              />
            </label>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={newAddress.is_default}
                onChange={(event) => setNewAddress((prev) => ({ ...prev, is_default: event.target.checked }))}
              />
              Set as default
            </label>

            <button className="btn btn--ghost" type="submit">
              Save address
            </button>
          </form>

          <div className="card order-summary">
            <h3>Order estimate</h3>
            <p>
              <span>Subtotal</span>
              <strong>{formatMoney(subtotal)}</strong>
            </p>
            <p>
              <span>Shipping</span>
              <strong>{formatMoney(Number(shippingTotal || 0))}</strong>
            </p>
            <p>
              <span>Tax</span>
              <strong>Applied at payment step</strong>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
