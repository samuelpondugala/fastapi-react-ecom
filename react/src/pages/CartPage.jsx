import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { formatMoney } from '../lib/format';
import { successToast } from '../lib/toast';

export default function CartPage() {
  const { token } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadCart() {
    setLoading(true);
    setError('');
    try {
      const data = await api.cart.getMine(token);
      setCart(data);
    } catch (err) {
      setError(err.message || 'Could not load cart.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCart();
  }, []);

  async function updateQty(itemId, quantity) {
    try {
      await api.cart.updateItem(token, itemId, { quantity: Math.max(1, quantity) });
      await loadCart();
      successToast('Cart updated.');
    } catch (err) {
      setError(err.message || 'Could not update quantity.');
    }
  }

  async function removeItem(itemId) {
    try {
      await api.cart.removeItem(token, itemId);
      await loadCart();
      successToast('Item removed from cart.');
    } catch (err) {
      setError(err.message || 'Could not remove item.');
    }
  }

  async function clearCart() {
    try {
      await api.cart.clearMine(token);
      await loadCart();
      successToast('Cart cleared.');
    } catch (err) {
      setError(err.message || 'Could not clear cart.');
    }
  }

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
      <div className="line-item">
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

  if (loading) {
    return (
      <div className="centered-screen">
        <div className="loader" />
        <p>Loading cart...</p>
      </div>
    );
  }

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>Cart</h1>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      {(cart?.items || []).length === 0 ? (
        <div className="card muted">
          Your cart is empty. <Link to="/catalog">Explore products</Link>.
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Qty</th>
                  <th>Unit price</th>
                  <th>Total</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {cart.items.map((item) => (
                  <tr key={item.id}>
                    <td>{renderItemIdentity(item)}</td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={item.quantity}
                        onChange={(event) => updateQty(item.id, Number(event.target.value) || 1)}
                      />
                    </td>
                    <td>{formatMoney(item.unit_price)}</td>
                    <td>{formatMoney(Number(item.unit_price) * Number(item.quantity))}</td>
                    <td>
                      <button type="button" className="btn btn--small btn--danger" onClick={() => removeItem(item.id)}>
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="order-summary card">
            <h3>Summary</h3>
            <p>
              <span>Subtotal</span>
              <strong>{formatMoney(subtotal)}</strong>
            </p>

            <div className="row-gap">
              <button type="button" className="btn btn--ghost" onClick={clearCart}>
                Clear cart
              </button>
              <Link className="btn" to="/checkout">
                Continue to checkout
              </Link>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
