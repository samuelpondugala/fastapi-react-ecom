import { Link, useParams, useSearchParams } from 'react-router-dom';

import { formatPaymentProvider, formatPaymentReference } from '../lib/format';

function SuccessIcon() {
  return (
    <svg viewBox="0 0 120 120" className="payment-result-icon" aria-hidden="true">
      <circle className="payment-result-icon__disc payment-result-icon__disc--success" cx="60" cy="60" r="46" />
      <path className="payment-result-icon__mark" d="M38 61.5 53 76l30-31" />
    </svg>
  );
}

function FailureIcon() {
  return (
    <svg viewBox="0 0 120 120" className="payment-result-icon" aria-hidden="true">
      <circle className="payment-result-icon__disc payment-result-icon__disc--failure" cx="60" cy="60" r="46" />
      <path className="payment-result-icon__mark" d="M43 43 77 77" />
      <path className="payment-result-icon__mark" d="M77 43 43 77" />
    </svg>
  );
}

export default function PaymentResultPage() {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();

  const status = searchParams.get('status') === 'success' ? 'success' : 'failure';
  const provider = searchParams.get('provider');
  const transactionRef = searchParams.get('ref');
  const orderNumber = searchParams.get('order');
  const message = searchParams.get('message');

  const isSuccess = status === 'success';
  const title = isSuccess ? 'Payment successful' : 'Payment unsuccessful';
  const subtitle = isSuccess
    ? 'Your order is confirmed and the payment has been recorded.'
    : message || 'No order was placed. Your cart has been restored so you can try again.';

  return (
    <section className={`payment-result-screen payment-result-screen--${status}`}>
      <div className="payment-result-card">
        {isSuccess ? <SuccessIcon /> : <FailureIcon />}
        <p className="payment-result-card__eyebrow">{isSuccess ? 'Payment complete' : 'Payment interrupted'}</p>
        <h1>{title}</h1>
        <p className="payment-result-card__copy">{subtitle}</p>

        <div className="payment-result-meta">
          <p>
            <span>Order</span>
            <strong>{orderNumber || `#${orderId}`}</strong>
          </p>
          <p>
            <span>Mode</span>
            <strong>{formatPaymentProvider(provider)}</strong>
          </p>
          {provider && (
            <p>
              <span>{provider === 'cod' ? 'Payment' : 'Transaction ID'}</span>
              <strong>{formatPaymentReference(provider, transactionRef)}</strong>
            </p>
          )}
        </div>

        <div className="row-gap payment-result-card__actions">
          {isSuccess ? (
            <>
              <Link className="btn" to={`/orders/${orderId}`}>
                View order
              </Link>
              <Link className="btn btn--ghost" to="/orders">
                All orders
              </Link>
            </>
          ) : (
            <>
              <Link className="btn" to="/cart">
                Back to cart
              </Link>
              <Link className="btn btn--ghost" to="/checkout">
                Checkout again
              </Link>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
