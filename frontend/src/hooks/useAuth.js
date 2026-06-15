// frontend/src/hooks/useAuth.js
export function getStoredKey() {
  // Priority: sessionStorage (login page) > env var (local dev)
  return sessionStorage.getItem('et_api_key') ||
         import.meta.env.VITE_API_KEY ||
         ''
}

export function clearStoredKey() {
  sessionStorage.removeItem('et_api_key')
}

export function isAuthenticated() {
  return Boolean(getStoredKey())
}
