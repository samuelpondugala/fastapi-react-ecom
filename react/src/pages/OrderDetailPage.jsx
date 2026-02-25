import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import StatusPill from '../components/StatusPill';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { formatDate, formatMoney } from '../lib/format';

const initialPaymentPayload = {
  provider: 'manual_free',
  currency: 'USD',
  apply_tax: false,
  tax_mode: 'none',
  tax_value: '0.00',
  simulate_failure: false,
  metadata: {},
};

export default function OrderDetailPage() {
  const { token, isAdmin } = useAuth();
  const { orderId } = useParams();

  const [order, setOrder] = useState(null);
  const [gateways, setGateways] = useState([]);
  const [payload, setPayload] = useState(initialPaymentPayload);
  const [quote, setQuote] = useState(null);
  const [paymentResult, setPaymentResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function loadOrder() {
    setLoading(true);
    setError('');
    try {
      const [orderData, gatewayData] = await Promise.all([
        api.orders.getById(token, orderId),
        api.orders.listFreeGateways(token),
      ]);
      setOrder(orderData);
      setGateways(gatewayData);
    } catch (err) {
      setError(err.message || 'Could not load order.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOrder();
  }, [orderId]);

  function setField(name, value) {
    setPayload((prev) => ({ ...prev, [name]: value }));
  }

  async function getQuote() {
    try {
      const result = await api.orders.quotePayment(token, orderId, {
        ...payload,
        tax_value: payload.tax_value,
      });
      setQuote(result);
      setError('');
    } catch (err) {
      setError(err.message || 'Could not generate payment quote.');
    }
  }

  async function submitPayment() {
    try {
      const result = await api.orders.payOrder(token, orderId, {
        ...payload,
        tax_value: payload.tax_value,
      });
      setPaymentResult(result);
      setOrder(result.order);
      setQuote(result.quote);
      setError('');
    } catch (err) {
      setError(err.message || 'Payment failed.');
    }
  }

  if (loading) {
    return (
      <div className="centered-screen">
        <div className="loader" />
        <p>Loading order...</p>
      </div>
    );
  }

  if (!order) return <div className="alert alert--error">Order not found.</div>;

  return (
    <section className="section fade-in">
      <div className="section__head">
        <h1>Order #{order.order_number}</h1>
        <p className="muted">Taxes are added only at payment stage.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="split-grid">
        <div className="stack-gap">
          <div className="card">
            <h3>Order Summary</h3>
            <p>
              <strong>Status:</strong> <StatusPill value={order.status} />
            </p>
            <p>
              <strong>Payment:</strong> <StatusPill value={order.payment_status} />
            </p>
            <p>
              <strong>Placed:</strong> {formatDate(order.placed_at)}
            </p>

            <div className="money-grid">
              <p>
                <span>Subtotal</span>
                <strong>{formatMoney(order.subtotal)}</strong>
              </p>
              <p>
                <span>Shipping</span>
                <strong>{formatMoney(order.shipping_total)}</strong>
              </p>
              <p>
                <span>Tax</span>
                <strong>{formatMoney(order.tax_total)}</strong>
              </p>
              <p>
                <span>Grand total</span>
                <strong>{formatMoney(order.grand_total)}</strong>
              </p>
            </div>
          </div>

          <div className="card">
            <h3>Items</h3>
            <ul className="list-clean">
              {order.items.map((item) => (
                <li key={item.id} className="order-line">
                  <div className="line-item line-item--compact">
                    {item.product_id ? (
                      <Link
                        to={`/products/${item.product_id}`}
                        className="line-item__media"
                        aria-label={`View ${item.product_name_snapshot}`}
                      >
                        {item.product_image_url ? (
                          <img
                            src={item.product_image_url}
                            alt={item.product_image_alt || item.product_name_snapshot}
                            loading="lazy"
                          />
                        ) : (
                          <div className="image-placeholder">No image</div>
                        )}
                      </Link>
                    ) : (
                      <div className="line-item__media">
                        {item.product_image_url ? (
                          <img
                            src={item.product_image_url}
                            alt={item.product_image_alt || item.product_name_snapshot}
                            loading="lazy"
                          />
                        ) : (
                          <div className="image-placeholder">No image</div>
                        )}
                      </div>
                    )}

                    <div className="line-item__meta">
                      {item.product_id ? (
                        <Link to={`/products/${item.product_id}`} className="line-item__name">
                          {item.product_name_snapshot}
                        </Link>
                      ) : (
                        <p className="line-item__name">{item.product_name_snapshot}</p>
                      )}
                      <p className="small muted">SKU: {item.variant_sku || item.sku_snapshot}</p>
                    </div>
                  </div>

                  <p className="muted small">
                    {item.quantity} x {formatMoney(item.unit_price)} = <strong>{formatMoney(item.line_total)}</strong>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="card">
          <h3>Payment Studio</h3>
          {isAdmin && <p className="chip">Admin can pay any order ID.</p>}

          <label>
            Gateway
            <select value={payload.provider} onChange={(event) => setField('provider', event.target.value)}>
              {gateways.map((gateway) => (
                <option key={gateway.code} value={gateway.code}>
                  {gateway.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Currency
            <input value={payload.currency} onChange={(event) => setField('currency', event.target.value.toUpperCase())} />
          </label>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={payload.apply_tax}
              onChange={(event) => setField('apply_tax', event.target.checked)}
            />
            Apply tax at payment
          </label>

          <div className="grid-two">
            <label>
              Tax mode
              <select value={payload.tax_mode} onChange={(event) => setField('tax_mode', event.target.value)}>
                <option value="none">none</option>
                <option value="fixed">fixed</option>
                <option value="percent">percent</option>
              </select>
            </label>

            <label>
              Tax value
              <input
                type="number"
                min="0"
                step="0.01"
                value={payload.tax_value}
                onChange={(event) => setField('tax_value', event.target.value)}
              />
            </label>
          </div>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={payload.simulate_failure}
              onChange={(event) => setField('simulate_failure', event.target.checked)}
            />
            Simulate failure (mock gateway only)
          </label>

          <div className="row-gap">
            <button className="btn btn--ghost" type="button" onClick={getQuote}>
              Get Quote
            </button>
            <button className="btn" type="button" onClick={submitPayment}>
              Pay now
            </button>
          </div>

          {quote && (
            <div className="card card--inset">
              <h4>Quote</h4>
              <p>
                Base: <strong>{formatMoney(quote.base_amount)}</strong>
              </p>
              <p>
                Tax: <strong>{formatMoney(quote.tax_amount)}</strong>
              </p>
              <p>
                Gateway fee: <strong>{formatMoney(quote.gateway_fee)}</strong>
              </p>
              <p>
                Total: <strong>{formatMoney(quote.total_amount)}</strong>
              </p>
            </div>
          )}

          {paymentResult && (
            <div className="card card--inset">
              <h4>Payment Result</h4>
              <p>
                Status: <StatusPill value={paymentResult.payment.status} />
              </p>
              <p className="small muted">Reference: {paymentResult.payment.transaction_ref}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
