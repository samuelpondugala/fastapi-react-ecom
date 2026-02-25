export default function StatusPill({ value }) {
  const normalized = String(value || '').toLowerCase();
  const className = ['status-pill'];

  if (
    normalized.includes('paid') ||
    normalized.includes('processing') ||
    normalized.includes('active') ||
    normalized === 'ok' ||
    normalized === 'ready'
  ) {
    className.push('status-pill--good');
  } else if (normalized.includes('pending') || normalized.includes('unpaid') || normalized.includes('draft')) {
    className.push('status-pill--warn');
  } else if (normalized.includes('failed') || normalized.includes('inactive')) {
    className.push('status-pill--bad');
  }

  return <span className={className.join(' ')}>{value || 'unknown'}</span>;
}
