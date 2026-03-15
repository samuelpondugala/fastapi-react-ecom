import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import StatusPill from '../components/StatusPill';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import {
  estimateDeliveryDate,
  formatDate,
  formatMoney,
  formatPaymentProvider,
  formatPaymentReference,
} from '../lib/format';
import { errorToast, successToast } from '../lib/toast';

const RAZORPAY_SCRIPT_ID = 'razorpay-checkout-script';
const RAZORPAY_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

function loadRazorpayCheckoutScript() {
  if (window.Razorpay) return Promise.resolve(true);

  const existing = document.getElementById(RAZORPAY_SCRIPT_ID);
  if (existing) {
    return new Promise((resolve) => {
      existing.addEventListener('load', () => resolve(true), { once: true });
      existing.addEventListener('error', () => resolve(false), { once: true });
    });
  }

  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.id = RAZORPAY_SCRIPT_ID;
    script.src = RAZORPAY_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

const paymentModeDefinitions = [
  {
    provider: 'cod',
    label: 'Cash on Delivery',
    description: 'Bypass online payment and collect cash when the order arrives.',
  },
  { provider: 'razorpay_upi', label: 'UPI', description: 'Google Pay / PhonePe / Paytm UPI' },
  { provider: 'razorpay_card', label: 'Credit / Debit Card', description: 'Visa / MasterCard / RuPay / Amex' },
];

const partnerBanks = [
  'State Bank of India',
  'HDFC Bank',
  'ICICI Bank',
  'Axis Bank',
  'Kotak Mahindra Bank',
  'Punjab National Bank',
  'Bank of Baroda',
  'Canara Bank',
  'IndusInd Bank',
];

const initialPaymentPayload = {
  provider: 'razorpay_upi',
  currency: 'INR',
  apply_tax: false,
  tax_mode: 'none',
  tax_value: '0.00',
  metadata: {},
};

function isRazorpayProvider(provider) {
  return provider === 'razorpay_upi' || provider === 'razorpay_card';
}

function buildPaymentResultPath(orderId, status, details = {}) {
  const params = new URLSearchParams({ status });
  Object.entries(details).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });
  return `/orders/${orderId}/payment-result?${params.toString()}`;
}

export default function OrderDetailPage() {
  const navigate = useNavigate();
  const { token, isAdmin, user } = useAuth();
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();

  const checkoutFlow = searchParams.get('checkout') === '1';
  const autoStartPayment = searchParams.get('autostart') === '1';

  const [order, setOrder] = useState(null);
  const [gateways, setGateways] = useState([]);
  const [payload, setPayload] = useState(initialPaymentPayload);
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [processingRazorpay, setProcessingRazorpay] = useState(false);
  const [processingCod, setProcessingCod] = useState(false);
  const autoLaunchAttemptedRef = useRef(false);

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
  }, [orderId, token]);

  useEffect(() => {
    const providerFromQuery = searchParams.get('provider');
    if (!providerFromQuery) return;
    const allowedProviders = new Set(paymentModeDefinitions.map((item) => item.provider));
    if (!allowedProviders.has(providerFromQuery)) return;
    setPayload((prev) => ({ ...prev, provider: providerFromQuery }));
  }, [searchParams]);

  const availableProviders = useMemo(() => new Set(gateways.map((item) => item.code)), [gateways]);
  const selectedPaymentDefinition =
    paymentModeDefinitions.find((option) => option.provider === payload.provider) || paymentModeDefinitions[0];

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

  async function navigateToFailureScreen(message) {
    if (!checkoutFlow) return;

    try {
      await api.orders.cancelUnpaid(token, orderId);
    } catch (err) {
      if (err?.status === 409) {
        successToast('Payment state changed while closing checkout. Please confirm the order status.');
        navigate(`/orders/${orderId}`, { replace: true });
        return;
      }
    }

    navigate(
      buildPaymentResultPath(orderId, 'failure', {
        provider: payload.provider,
        message,
      }),
      { replace: true }
    );
  }

  function navigateToSuccessScreen(result) {
    navigate(
      buildPaymentResultPath(orderId, 'success', {
        provider: result.payment.provider,
        ref: result.payment.transaction_ref,
        order: result.order.order_number,
      }),
      { replace: true }
    );
  }

  async function submitCodPayment() {
    setProcessingCod(true);
    setError('');
    try {
      const result = await api.orders.payOrder(token, orderId, {
        provider: 'cod',
        currency: 'INR',
        apply_tax: false,
        tax_mode: 'none',
        tax_value: '0.00',
        metadata: {
          initiated_from: checkoutFlow ? 'checkout' : 'order_detail',
        },
      });
      setOrder(result.order);
      setQuote(result.quote);
      successToast('Cash on Delivery enabled for this order.');
      navigate(`/orders/${result.order.id}`, { replace: true });
    } catch (err) {
      setError(err.message || 'Could not enable Cash on Delivery.');
    } finally {
      setProcessingCod(false);
    }
  }

  async function submitPayment() {
    if (payload.provider === 'cod') {
      await submitCodPayment();
      return;
    }

    setProcessingRazorpay(true);
    try {
      const scriptLoaded = await loadRazorpayCheckoutScript();
      if (!scriptLoaded || !window.Razorpay) {
        throw new Error('Unable to load Razorpay checkout script.');
      }

      const checkoutOrder = await api.orders.createRazorpayOrder(token, orderId, {
        provider: payload.provider,
        metadata: {
          ...(payload.metadata || {}),
          initiated_from: checkoutFlow ? 'checkout' : 'order_detail',
        },
      });

      const method =
        payload.provider === 'razorpay_upi'
          ? {
              upi: true,
              card: false,
              netbanking: false,
              wallet: false,
              emi: false,
              paylater: false,
            }
          : {
              upi: false,
              card: true,
              netbanking: false,
              wallet: false,
              emi: false,
              paylater: false,
            };

      const razorpayOptions = {
        key: checkoutOrder.key_id,
        amount: checkoutOrder.amount,
        currency: checkoutOrder.currency,
        name: 'Commerce Studio',
        description: `Order #${checkoutOrder.order_number}`,
        order_id: checkoutOrder.razorpay_order_id,
        method,
        prefill: {
          name: user?.full_name || undefined,
          email: user?.email || undefined,
        },
        notes: {
          internal_order_id: String(checkoutOrder.internal_order_id),
        },
        theme: {
          color: '#008768',
        },
        handler: async (response) => {
          try {
            const result = await api.orders.verifyRazorpayPayment(token, orderId, {
              provider: payload.provider,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              metadata: payload.metadata,
            });
            setOrder(result.order);
            setQuote(result.quote);
            setError('');
            successToast('Razorpay payment verified successfully.');
            navigateToSuccessScreen(result);
          } catch (err) {
            const message =
              err.message || 'Payment was received but could not be verified automatically. Please refresh the order.';
            setError(message);
            errorToast(message);
          } finally {
            setProcessingRazorpay(false);
          }
        },
        modal: {
          ondismiss: () => {
            setProcessingRazorpay(false);
            if (checkoutFlow) {
              void navigateToFailureScreen('Payment window closed before completion.');
            }
          },
        },
      };

      const razorpay = new window.Razorpay(razorpayOptions);
      razorpay.on('payment.failed', (event) => {
        setProcessingRazorpay(false);
        const message = event?.error?.description || 'Payment failed in Razorpay.';
        setError(message);
        errorToast(message);
        if (checkoutFlow) {
          void navigateToFailureScreen(message);
        }
      });
      razorpay.open();
    } catch (err) {
      setProcessingRazorpay(false);
      setError(err.message || 'Unable to start Razorpay checkout.');
    }
  }

  useEffect(() => {
    if (loading || !order || !autoStartPayment || autoLaunchAttemptedRef.current) return;
    if (order.payment_status !== 'unpaid') return;
    if (!isRazorpayProvider(payload.provider)) return;
    if (availableProviders.size > 0 && !availableProviders.has(payload.provider)) return;

    autoLaunchAttemptedRef.current = true;
    void submitPayment();
  }, [autoStartPayment, availableProviders, loading, order, payload.provider]);

  if (loading) {
    return (
      <div className="centered-screen">
        <div className="loader" />
        <p>Loading order...</p>
      </div>
    );
  }

  if (!order) return <div className="alert alert--error">Order not found.</div>;

  const expectedDelivery = estimateDeliveryDate(5);
  const paymentModeLabel = formatPaymentProvider(order.payment_provider);
  const paymentReference = formatPaymentReference(order.payment_provider, order.payment_transaction_ref);
  const canCollectPayment = order.payment_status === 'unpaid';

  return (
    <section className="section fade-in order-detail-page">
      <div className="section__head">
        <h1>Order #{order.order_number}</h1>
        <p className="muted">All timestamps are shown in IST.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="split-grid order-detail-layout">
        <div className="stack-gap order-detail-layout__left">
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
                <span>Delivery</span>
                <strong>{formatMoney(order.shipping_total)}</strong>
              </p>
              <p>
                <span>Discount</span>
                <strong>-{formatMoney(order.discount_total)}</strong>
              </p>
              <p>
                <span>Tax</span>
                <strong>{formatMoney(order.tax_total)}</strong>
              </p>
              <p>
                <span>Grand Total</span>
                <strong>{formatMoney(order.grand_total)}</strong>
              </p>
            </div>
          </div>

          <div className="card">
            <h3>Payment Detail</h3>
            <div className="payment-detail-grid">
              <p>
                <span>Mode</span>
                <strong>{paymentModeLabel}</strong>
              </p>
              <p>
                <span>Status</span>
                <strong>{order.payment_record_status || order.payment_status}</strong>
              </p>
              <p>
                <span>{order.payment_provider === 'cod' ? 'Payment' : 'Transaction ID'}</span>
                <strong>{paymentReference}</strong>
              </p>
              <p>
                <span>Recorded</span>
                <strong>{order.payment_paid_at ? formatDate(order.payment_paid_at) : 'Pending at delivery'}</strong>
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
                      <p className="small muted">Estimated delivery: {expectedDelivery}</p>
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

        <div className="stack-gap order-detail-layout__right">
          <div className="card">
            <h3>Customer & Fulfillment</h3>
            <div className="payment-detail-grid">
              <p>
                <span>Customer</span>
                <strong>{order.customer_name || order.customer_email || `User #${order.user_id}`}</strong>
              </p>
              <p>
                <span>Email</span>
                <strong>{order.customer_email || '--'}</strong>
              </p>
              <p>
                <span>Shipping address</span>
                <strong>{order.shipping_address_id ? `Address #${order.shipping_address_id}` : 'Not set'}</strong>
              </p>
              <p>
                <span>Billing address</span>
                <strong>{order.billing_address_id ? `Address #${order.billing_address_id}` : 'Not set'}</strong>
              </p>
            </div>
          </div>

          <div className="card">
            <h3>Step 2: Select Payment Mode</h3>
            {canCollectPayment ? (
              <div className="payment-modes">
                {paymentModeDefinitions
                  .filter((option) => availableProviders.size === 0 || availableProviders.has(option.provider))
                  .map((option) => (
                    <button
                      key={option.provider}
                      type="button"
                      className={`payment-mode-card ${
                        payload.provider === option.provider ? 'payment-mode-card--active' : ''
                      }`}
                      onClick={() => setField('provider', option.provider)}
                    >
                      <strong>{option.label}</strong>
                      <p className="small muted">{option.description}</p>
                    </button>
                  ))}
              </div>
            ) : (
              <div className="card card--inset">
                <p>
                  Payment mode: <strong>{paymentModeLabel}</strong>
                </p>
                <p className="small muted">
                  {order.payment_provider === 'cod'
                    ? 'This order will be paid when it is delivered.'
                    : `Transaction ID: ${paymentReference}`}
                </p>
              </div>
            )}
          </div>

          <div className="card">
            <h3>Partner Banks</h3>
            <div className="bank-carousel" aria-label="Supported partner banks">
              <div className="bank-carousel__track">
                {[...partnerBanks, ...partnerBanks].map((bank, index) => (
                  <span key={`${bank}-${index}`} className="chip">
                    {bank}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Step 3: Quote & Pay</h3>
            {isAdmin && <p className="chip">Admin can inspect or complete payment for any order.</p>}
            {!canCollectPayment && (
              <div className="card card--inset">
                <p>
                  <strong>Payment already configured</strong>
                </p>
                <p className="small muted">No further action is needed from this screen.</p>
              </div>
            )}

            {canCollectPayment && (
              <>
                <label>
                  Currency
                  <input
                    value={payload.currency}
                    onChange={(event) => setField('currency', event.target.value.toUpperCase())}
                    disabled={payload.provider === 'cod'}
                  />
                </label>

                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={payload.apply_tax}
                    onChange={(event) => setField('apply_tax', event.target.checked)}
                    disabled={payload.provider === 'cod'}
                  />
                  Apply tax at payment
                </label>

                <div className="grid-two">
                  <label>
                    Tax mode
                    <select
                      value={payload.tax_mode}
                      onChange={(event) => setField('tax_mode', event.target.value)}
                      disabled={payload.provider === 'cod'}
                    >
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
                      disabled={payload.provider === 'cod'}
                    />
                  </label>
                </div>

                <div className="row-gap">
                  <button className="btn btn--ghost" type="button" onClick={getQuote}>
                    Get Quote
                  </button>
                  <button
                    className="btn"
                    type="button"
                    onClick={submitPayment}
                    disabled={processingRazorpay || processingCod}
                  >
                    {payload.provider === 'cod'
                      ? processingCod
                        ? 'Saving COD...'
                        : 'Confirm COD'
                      : processingRazorpay
                        ? 'Opening Razorpay...'
                        : `Pay with ${selectedPaymentDefinition.label}`}
                  </button>
                </div>
              </>
            )}

            {quote && (
              <div className="card card--inset">
                <h4>Payment Quote</h4>
                <p>
                  Base: <strong>{formatMoney(quote.base_amount)}</strong>
                </p>
                <p>
                  Tax: <strong>{formatMoney(quote.tax_amount)}</strong>
                </p>
                <p>
                  Gateway Fee: <strong>{formatMoney(quote.gateway_fee)}</strong>
                </p>
                <p>
                  Total: <strong>{formatMoney(quote.total_amount)}</strong>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
