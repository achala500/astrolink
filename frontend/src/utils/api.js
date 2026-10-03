// Same-origin API helper. Tokens are optional for local/offline installations.
// For a private cloud deployment, provide VITE_ASTROLINK_API_TOKEN at build time.
export function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = import.meta.env.VITE_ASTROLINK_API_TOKEN;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

export function adminApiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = import.meta.env.VITE_ASTROLINK_ADMIN_TOKEN || import.meta.env.VITE_ASTROLINK_API_TOKEN;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}
