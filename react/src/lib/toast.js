export const TOAST_EVENT = 'ecom:toast';

export function pushToast({ type = 'info', message, duration = 4200 } = {}) {
  if (!message) return;
  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT, {
      detail: {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        type,
        message,
        duration,
      },
    }),
  );
}

export function successToast(message, duration) {
  pushToast({ type: 'success', message, duration });
}

export function errorToast(message, duration) {
  pushToast({ type: 'error', message, duration });
}
