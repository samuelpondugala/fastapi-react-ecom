import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { estimateDeliveryDate, formatMoney } from '../lib/format';
import { errorToast, successToast } from '../lib/toast';

const FREE_DELIVERY_THRESHOLD = 1000;
const DELIVERY_CHARGE = 100;
const RAZORPAY_SCRIPT_ID = 'razorpay-checkout-script';
const RAZORPAY_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

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

const paymentOptions = [
  {
    id: 'cod',
    label: 'Cash on Delivery',
    description: 'Confirm the order now and pay when it is delivered',
    provider: 'cod',
    methods: ['Pay at doorstep'],
  },
  {
    id: 'upi',
    label: 'UPI',
    description: 'Instant payment via UPI apps',
    provider: 'razorpay_upi',
    methods: ['GPay', 'PhonePe', 'Paytm'],
  },
  {
    id: 'card',
    label: 'Credit / Debit Card',
    description: 'Visa, MasterCard, RuPay, Amex',
    provider: 'razorpay_card',
    methods: ['Credit Card', 'Debit Card'],
  },
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
  'IDFC FIRST Bank',
];

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

function buildPaymentResultPath(status, details = {}) {
  const params = new URLSearchParams({ status });
  Object.entries(details).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });
  return `/payment-result?${params.toString()}`;
}

function buildRazorpayDisplayConfig(provider) {
  if (provider !== 'razorpay_upi' && provider !== 'razorpay_card') {
    return undefined;
  }

  return {
    display: {
      sequence: [provider === 'razorpay_upi' ? 'upi' : 'card'],
      preferences: {
        // Keep Razorpay's supported defaults visible so checkout does not fail
        // when a method is unavailable for the current device/account context.
        show_default_blocks: true,
      },
    },
  };
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { token, user } = useAuth();

  const [step, setStep] = useState(1);
  const [cart, setCart] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [shippingAddressId, setShippingAddressId] = useState('');
  const [billingAddressId, setBillingAddressId] = useState('');
  const [paymentOptionId, setPaymentOptionId] = useState('');
  const [couponInput, setCouponInput] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState(null);
  const [dismissShippingHint, setDismissShippingHint] = useState(false);
  const [newAddress, setNewAddress] = useState(emptyAddress);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function loadData() {
    setLoading(true);
    setError('');
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

  const shippingCharge = subtotal >= FREE_DELIVERY_THRESHOLD ? 0 : DELIVERY_CHARGE;
  const amountForFreeShipping = Math.max(0, FREE_DELIVERY_THRESHOLD - subtotal);

  const discountAmount = useMemo(() => {
    if (!appliedCoupon) return 0;
    const rawValue = Number(appliedCoupon.value || 0);
    if (!Number.isFinite(rawValue) || rawValue <= 0) return 0;
    if (appliedCoupon.type === 'percent') {
      return Math.min(subtotal, (subtotal * rawValue) / 100);
    }
    return Math.min(subtotal, rawValue);
  }, [appliedCoupon, subtotal]);

  const payableTotal = Math.max(0, subtotal - discountAmount + shippingCharge);
  const selectedPaymentOption = paymentOptions.find((item) => item.id === paymentOptionId) || null;
  const estimatedDelivery = estimateDeliveryDate(4);

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
          <p className="small muted">Estimated delivery: {estimatedDelivery}</p>
        </div>
      </div>
    );
  }

  async function applyCoupon() {
    const couponCode = couponInput.trim().toUpperCase();
    if (!couponCode) {
      errorToast('Enter a valid coupon code.');
      return;
    }

    try {
      const coupons = await api.coupons.list(token, { active_only: true, limit: 500 });
      const matched = coupons.find((item) => item.code?.toUpperCase() === couponCode);

      if (!matched) {
        setAppliedCoupon(null);
        errorToast('Coupon not found or inactive.');
        return;
      }

      if (matched.min_order_amount && subtotal < Number(matched.min_order_amount)) {
        setAppliedCoupon(null);
        errorToast(`Coupon needs minimum cart value of ${formatMoney(matched.min_order_amount)}`);
        return;
      }

      setAppliedCoupon(matched);
      successToast(`Coupon ${matched.code} applied.`);
    } catch (err) {
      setAppliedCoupon(null);
      setError(err.message || 'Could not validate coupon.');
    }
  }

  async function createAddress(event) {
    event.preventDefault();
    setError('');
    try {
      await api.addresses.createMine(token, { ...newAddress, country: 'IND' });
      setNewAddress(emptyAddress);
      await loadData();
      successToast('Address saved.');
    } catch (err) {
      setError(err.message || 'Could not create address.');
    }
  }

  function goToNextStep() {
    if (step === 1) {
      if ((cart?.items || []).length === 0) {
        errorToast('Your cart is empty.');
        return;
      }
      setStep(2);
      return;
    }

    if (step === 2) {
      if (!shippingAddressId) {
        errorToast('Please select a shipping address.');
        return;
      }
      if (!billingAddressId) {
        errorToast('Please select a billing address.');
        return;
      }
      if (!selectedPaymentOption) {
        errorToast('Please select a payment method before continuing.');
        return;
      }
      setStep(3);
    }
  }

  function goToPreviousStep() {
    setStep((prev) => Math.max(1, prev - 1));
  }

  async function placeCodOrder() {
    const order = await api.orders.checkout(token, {
      shipping_address_id: shippingAddressId ? Number(shippingAddressId) : null,
      billing_address_id: billingAddressId ? Number(billingAddressId) : null,
      coupon_code: appliedCoupon?.code || null,
      shipping_total: String(shippingCharge.toFixed(2)),
      tax_total: '0.00',
    });

    const codResult = await api.orders.payOrder(token, order.id, {
      provider: 'cod',
      currency: 'INR',
      apply_tax: false,
      tax_mode: 'none',
      tax_value: '0.00',
      metadata: {
        initiated_from: 'checkout',
      },
    });

    successToast('Order placed with Cash on Delivery.');
    navigate(`/orders/${codResult.order.id}`, { replace: true });
  }

  async function placeOnlineOrder() {
    const scriptLoaded = await loadRazorpayCheckoutScript();
    if (!scriptLoaded || !window.Razorpay) {
      throw new Error('Unable to load Razorpay checkout script.');
    }

    const checkoutIntent = await api.orders.startCheckoutRazorpay(token, {
      provider: selectedPaymentOption.provider,
      shipping_address_id: shippingAddressId ? Number(shippingAddressId) : null,
      billing_address_id: billingAddressId ? Number(billingAddressId) : null,
      coupon_code: appliedCoupon?.code || null,
      shipping_total: String(shippingCharge.toFixed(2)),
      tax_total: '0.00',
      metadata: {
        initiated_from: 'checkout',
      },
    });

    await new Promise((resolve, reject) => {
      const razorpay = new window.Razorpay({
        key: checkoutIntent.key_id,
        amount: checkoutIntent.amount,
        currency: checkoutIntent.currency,
        name: 'Commerce Studio',
        description:
          selectedPaymentOption.provider === 'razorpay_upi' ? 'Checkout payment · UPI' : 'Checkout payment · Card',
        order_id: checkoutIntent.razorpay_order_id,
        config: buildRazorpayDisplayConfig(selectedPaymentOption.provider),
        prefill: {
          name: user?.full_name || undefined,
          email: user?.email || undefined,
        },
        notes: {
          checkout_reference: String(checkoutIntent.checkout_reference),
        },
        theme: {
          color: '#008768',
        },
        handler: async (response) => {
          try {
            const result = await api.orders.completeCheckoutRazorpay(token, {
              provider: selectedPaymentOption.provider,
              checkout_token: checkoutIntent.checkout_token,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              metadata: {
                initiated_from: 'checkout',
              },
            });
            successToast('Payment successful.');
            navigate(
              buildPaymentResultPath('success', {
                orderId: result.order.id,
                provider: result.payment.provider,
                ref: result.payment.transaction_ref,
                order: result.order.order_number,
              }),
              { replace: true }
            );
            resolve();
          } catch (err) {
            reject(err);
          }
        },
        modal: {
          ondismiss: () => {
            reject(new Error('Payment window closed before completion.'));
          },
        },
      });

      razorpay.on('payment.failed', (event) => {
        reject(new Error(event?.error?.description || 'Payment failed in Razorpay.'));
      });

      razorpay.open();
    });
  }

  async function handleSubmitOrder() {
    if (!selectedPaymentOption) {
      errorToast('Please select a payment method.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      if (selectedPaymentOption.provider === 'cod') {
        await placeCodOrder();
        return;
      }

      await placeOnlineOrder();
    } catch (err) {
      const message = err.message || 'Checkout failed.';
      setError(message);
      navigate(
        buildPaymentResultPath('failure', {
          provider: selectedPaymentOption.provider,
          message,
        }),
        { replace: true }
      );
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
        <p className="muted">Step 1: Cart, Step 2: Payment Mode, Step 3: Confirm.</p>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="checkout-steps">
        {[1, 2, 3].map((value) => (
          <div key={value} className={`checkout-step ${step >= value ? 'checkout-step--active' : ''}`}>
            <span>{value}</span>
            <strong>
              {value === 1 ? 'Cart Review' : value === 2 ? 'Delivery & Payment' : 'Confirm Order'}
            </strong>
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="stack-gap">
          {!dismissShippingHint && subtotal < FREE_DELIVERY_THRESHOLD && (
            <div className="delivery-note">
              <p>
                Add items worth <strong>{formatMoney(amountForFreeShipping)}</strong> more to unlock free delivery.
              </p>
              <button type="button" className="delivery-note__close" onClick={() => setDismissShippingHint(true)}>
                x
              </button>
            </div>
          )}

          <div className="card">
            <h3>Items in Cart</h3>
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
        </div>
      )}

      {step === 2 && (
        <div className="split-grid">
          <div className="stack-gap">
            <div className="card">
              <h3>Delivery Addresses</h3>

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
            </div>

            <form className="card" onSubmit={createAddress}>
              <h3>Add Address</h3>
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
                    onChange={(event) => setNewAddress((prev) => ({ ...prev, country: event.target.value || 'IND' }))}
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

              <button className="btn btn--ghost" type="submit">
                Save address
              </button>
            </form>
          </div>

          <div className="stack-gap">
            <div className="card">
              <h3>Select Payment Mode</h3>
              <div className="payment-modes">
                {paymentOptions.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={`payment-mode-card ${paymentOptionId === option.id ? 'payment-mode-card--active' : ''}`}
                    onClick={() => setPaymentOptionId(option.id)}
                  >
                    <strong>{option.label}</strong>
                    <p className="small muted">{option.description}</p>
                    <p className="small muted">{option.methods.join(' • ')}</p>
                  </button>
                ))}
              </div>
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
              <h3>Apply Coupon</h3>
              <div className="row-gap">
                <input
                  type="text"
                  value={couponInput}
                  onChange={(event) => setCouponInput(event.target.value)}
                  placeholder="Enter coupon code"
                />
                <button type="button" className="btn btn--ghost" onClick={applyCoupon}>
                  Apply
                </button>
                {appliedCoupon && (
                  <button type="button" className="btn btn--ghost" onClick={() => setAppliedCoupon(null)}>
                    Remove
                  </button>
                )}
              </div>
              {appliedCoupon && (
                <p className="small muted">
                  Applied: <strong>{appliedCoupon.code}</strong>
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="split-grid">
          <div className="card">
            <h3>Order Review</h3>
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

          <div className="card order-summary">
            <h3>Payable Quote</h3>
            <p>
              <span>Subtotal</span>
              <strong>{formatMoney(subtotal)}</strong>
            </p>
            <p>
              <span>Delivery</span>
              <strong>{formatMoney(shippingCharge)}</strong>
            </p>
            <p>
              <span>Coupon Discount</span>
              <strong>-{formatMoney(discountAmount)}</strong>
            </p>
            <p>
              <span>Tax</span>
              <strong>Calculated at payment stage</strong>
            </p>
            <p>
              <span>Payment Mode</span>
              <strong>{selectedPaymentOption?.label || 'Not selected'}</strong>
            </p>
            <p>
              <span>Total</span>
              <strong>{formatMoney(payableTotal)}</strong>
            </p>
            <button className="btn" type="button" disabled={submitting || !selectedPaymentOption} onClick={handleSubmitOrder}>
              {submitting
                ? selectedPaymentOption?.provider === 'cod'
                  ? 'Placing COD order...'
                  : 'Opening payment...'
                : selectedPaymentOption?.provider === 'cod'
                  ? 'Place order'
                  : selectedPaymentOption
                    ? 'Continue to pay'
                    : 'Select payment method first'}
            </button>
          </div>
        </div>
      )}

      <div className="row-gap">
        {step > 1 && (
          <button type="button" className="btn btn--ghost" onClick={goToPreviousStep}>
            Back
          </button>
        )}
        {step < 3 && (
          <button type="button" className="btn" onClick={goToNextStep}>
            Continue
          </button>
        )}
      </div>
    </section>
  );
}
