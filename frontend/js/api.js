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
    return JSON.parse(localStorage.getItem("tm_user") || "null");
  } catch (e) {
    return null;
  }
}

function setStoredUser(user) {
  localStorage.setItem("tm_user", JSON.stringify(user));
}

function clearStoredUser() {
  localStorage.removeItem("tm_user");
}

function renderNavUser(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  const user = getStoredUser();

  if (!user) {
    el.innerHTML = `<a href="/login.html">Login</a> &nbsp;·&nbsp; <a href="/register.html">Register</a>`;
    return;
  }

  const initials = user.username.slice(0, 2).toUpperCase();
  el.innerHTML = `
    <span class="avatar">${initials}</span>
    <span class="muted">${user.username}</span>
    <button class="secondary" id="nav-logout-btn" style="margin-top:0;padding:8px 14px;">Logout</button>`;

  document.getElementById("nav-logout-btn").addEventListener("click", async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    clearStoredUser();
    window.location.href = "/login.html";
  });
}

function markActiveNav(page) {
  document.querySelectorAll(".nav-links a").forEach((a) => {
    if (a.dataset.page === page) a.classList.add("active");
  });
}
