import { errorToast } from './toast';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://localhost:8000/api/v1';

function createError(status, message, data) {
  const error = new Error(message || `Request failed with status ${status}`);
  error.status = status;
  error.data = data;
  return error;
}

function formatValidationIssue(issue) {
  if (issue == null) return '';
  if (typeof issue === 'string') return issue;
  if (typeof issue !== 'object') return String(issue);

  const loc = Array.isArray(issue.loc) ? issue.loc.join('.') : '';
  const msg = typeof issue.msg === 'string' ? issue.msg : '';
  if (loc && msg) return `${loc}: ${msg}`;
  if (msg) return msg;
  if (typeof issue.detail === 'string') return issue.detail;

  try {
    return JSON.stringify(issue);
  } catch {
    return 'Unknown error';
  }
}

function normalizeErrorMessage(data, fallback) {
  if (typeof data === 'string') return data || fallback;
  if (Array.isArray(data)) {
    const joined = data.map(formatValidationIssue).filter(Boolean).join('; ');
    return joined || fallback;
  }
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) return normalizeErrorMessage(data.detail, fallback);
    if (data.detail && typeof data.detail === 'object') return normalizeErrorMessage(data.detail, fallback);
    if (typeof data.message === 'string') return data.message;
    return formatValidationIssue(data);
  }
  return fallback;
}

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

async function request(path, { method = 'GET', token, body, query, headers = {}, suppressErrorToast = false } = {}) {
  const url = `${API_BASE_URL}${path}${buildQuery(query)}`;
  const finalHeaders = { ...headers };

  if (!(body instanceof FormData)) {
    finalHeaders['Content-Type'] = 'application/json';
  }
  if (token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method,
    credentials: 'include',
    headers: finalHeaders,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });

  const isJson = (response.headers.get('content-type') || '').includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const message = normalizeErrorMessage(data, response.statusText || 'Request failed');
    if (!suppressErrorToast) {
      errorToast(message || 'Request failed');
    }
    throw createError(response.status, message, data);
  }

  return data;
}

export const api = {
  request,
  health: {
    status: () => request('/health'),
    ready: () => request('/health/ready'),
  },
  auth: {
    register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
    login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
    me: (token, options = {}) => request('/auth/me', { token, ...options }),
    logout: () => request('/auth/logout', { method: 'POST', suppressErrorToast: true }),
  },
  users: {
    list: (token, query) => request('/users', { token, query }),
    getById: (token, id) => request(`/users/${id}`, { token }),
    listOrders: (token, id, query) => request(`/users/${id}/orders`, { token, query }),
    updateMe: (token, payload) => request('/users/me', { method: 'PATCH', token, body: payload }),
  },
  addresses: {
    listMine: (token) => request('/addresses/me', { token }),
    createMine: (token, payload) => request('/addresses/me', { method: 'POST', token, body: payload }),
    updateMine: (token, id, payload) =>
      request(`/addresses/me/${id}`, { method: 'PATCH', token, body: payload }),
    deleteMine: (token, id) => request(`/addresses/me/${id}`, { method: 'DELETE', token }),
  },
  categories: {
    list: (query) => request('/categories', { query }),
    create: (token, payload) => request('/categories', { method: 'POST', token, body: payload }),
    update: (token, id, payload) => request(`/categories/${id}`, { method: 'PATCH', token, body: payload }),
  },
  products: {
    list: (query) => request('/products', { query }),
    getById: (id) => request(`/products/${id}`),
    create: (token, payload) => request('/products', { method: 'POST', token, body: payload }),
    update: (token, id, payload) => request(`/products/${id}`, { method: 'PATCH', token, body: payload }),
    importDummyJson: (token, payload) =>
      request('/products/import/dummyjson', { method: 'POST', token, body: payload }),
    importFromJson: (token, payload) => request('/products/import/json', { method: 'POST', token, body: payload }),
  },
  cart: {
    getMine: (token) => request('/cart/me', { token }),
    addItem: (token, payload) => request('/cart/items', { method: 'POST', token, body: payload }),
    updateItem: (token, id, payload) => request(`/cart/items/${id}`, { method: 'PATCH', token, body: payload }),
    removeItem: (token, id) => request(`/cart/items/${id}`, { method: 'DELETE', token }),
    clearMine: (token) => request('/cart/clear', { method: 'DELETE', token }),
  },
  orders: {
    checkout: (token, payload) => request('/orders/checkout', { method: 'POST', token, body: payload }),
    startCheckoutRazorpay: (token, payload) =>
      request('/orders/checkout/razorpay/start', { method: 'POST', token, body: payload }),
    completeCheckoutRazorpay: (token, payload) =>
      request('/orders/checkout/razorpay/complete', { method: 'POST', token, body: payload }),
    listAdmin: (token, query) => request('/orders', { token, query }),
    listMine: (token, query) => request('/orders/me', { token, query }),
    getById: (token, id) => request(`/orders/${id}`, { token }),
    listFreeGateways: (token) => request('/orders/payment-gateways/free', { token }),
    quotePayment: (token, id, payload) =>
      request(`/orders/${id}/payment/quote`, { method: 'POST', token, body: payload }),
    payOrder: (token, id, payload) => request(`/orders/${id}/pay`, { method: 'POST', token, body: payload }),
    createRazorpayOrder: (token, id, payload) =>
      request(`/orders/${id}/payment/razorpay/order`, { method: 'POST', token, body: payload }),
    verifyRazorpayPayment: (token, id, payload) =>
      request(`/orders/${id}/payment/razorpay/verify`, { method: 'POST', token, body: payload }),
    cancelUnpaid: (token, id) => request(`/orders/${id}/cancel-unpaid`, { method: 'POST', token }),
  },
  coupons: {
    list: (token, query) => request('/coupons', { token, query }),
    create: (token, payload) => request('/coupons', { method: 'POST', token, body: payload }),
  },
  reviews: {
    listByProduct: (productId) => request(`/reviews/product/${productId}`),
    create: (token, payload) => request('/reviews', { method: 'POST', token, body: payload }),
  },
};

export { API_BASE_URL };
