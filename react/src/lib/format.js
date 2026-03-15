const USD_TO_INR_RATE = 83;
const PAYMENT_PROVIDER_LABELS = {
  cod: 'Cash on Delivery',
  razorpay_upi: 'UPI',
  razorpay_card: 'Card',
};

function toNumber(value) {
  const numberValue = typeof value === 'string' ? Number.parseFloat(value) : value;
  return Number.isFinite(numberValue) ? numberValue : 0;
}

export function formatMoney(value, currency = 'INR') {
  const numberValue = toNumber(value);
  const sourceCurrency = (currency || 'INR').toUpperCase();
  const displayCurrency = 'INR';
  const convertedValue = sourceCurrency === 'USD' ? numberValue * USD_TO_INR_RATE : numberValue;

  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: displayCurrency }).format(convertedValue);
}

export function formatDate(value) {
  if (!value) return '--';
  const date = new Date(value);
  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function estimateDeliveryDate(daysFromNow = 4) {
  const date = new Date();
  date.setDate(date.getDate() + Math.max(1, Number(daysFromNow) || 4));
  return date.toLocaleDateString('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    month: 'short',
    day: '2-digit',
  });
}

export function formatPaymentProvider(provider) {
  if (!provider) return 'Payment pending';
  return PAYMENT_PROVIDER_LABELS[provider] || provider.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatPaymentReference(provider, reference) {
  if (provider === 'cod') return 'COD';
  return reference || '--';
}
