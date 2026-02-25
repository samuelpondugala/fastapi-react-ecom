export function formatMoney(value, currency = 'USD') {
  const numberValue = typeof value === 'string' ? Number.parseFloat(value) : value;
  if (!Number.isFinite(numberValue)) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(numberValue);
}

export function formatDate(value) {
  if (!value) return '--';
  const date = new Date(value);
  return date.toLocaleString();
}
