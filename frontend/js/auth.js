/**
 * auth.js - Client-Side Authentication Manager
 *
 * Beginner-Friendly Explanation:
 * Communicates with backend endpoints (/api/auth/*) using HTTP fetch requests.
 * Manages user session state, handles login, registration, demo-guest login,
 * and updates user profile badges across pages.
 */

async function getCurrentUser() {
  try {
    const res = await fetch('/api/auth/me');
    if (!res.ok) return null;
    const data = await res.json();
    return data.authenticated ? data.user : null;
  } catch (err) {
    console.error("Auth check failed:", err);
    return null;
  }
}

async function loginUser(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return await res.json();
}

async function registerUser(username, password, fullName, location) {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      password,
      full_name: fullName,
      location: location || 'Delhi,IN'
    })
  });
  return await res.json();
}

async function loginAsGuest() {
  const res = await fetch('/api/guest-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

async function logoutUser() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } finally {
    window.location.href = '/login';
  }
}
