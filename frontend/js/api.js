const API_BASE = "/api";

async function apiFetch(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }

  return { ok: response.ok, status: response.status, data };
}

function showMessage(el, text, isError = false) {
  el.textContent = text;
  el.className = isError ? "message error" : "message success";
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("soclab_user") || "null");
  } catch (e) {
    return null;
  }
}

function setStoredUser(user) {
  localStorage.setItem("soclab_user", JSON.stringify(user));
}

function clearStoredUser() {
  localStorage.removeItem("soclab_user");
}

function renderUserBadge(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  const user = getStoredUser();
  el.textContent = user ? `Logged in as ${user.username} (id: ${user.id})` : "Not logged in";
}
