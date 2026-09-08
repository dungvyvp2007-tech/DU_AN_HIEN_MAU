/* Tiện ích dùng chung: thông báo toast, định dạng ngày giờ, hiển thị lỗi form. */

function ensureToastStack() {
  let stack = document.querySelector(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }
  return stack;
}

function toast(message, type = "info") {
  const stack = ensureToastStack();
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function showFormErrors(formEl, errors = {}) {
  formEl.querySelectorAll(".field.has-error").forEach((f) => f.classList.remove("has-error"));
  Object.entries(errors).forEach(([field, msg]) => {
    const wrap = formEl.querySelector(`[data-field="${field}"]`);
    if (wrap) {
      wrap.classList.add("has-error");
      const errEl = wrap.querySelector(".error-text");
      if (errEl) errEl.textContent = msg;
    }
  });
}

function clearFormErrors(formEl) {
  formEl.querySelectorAll(".field.has-error").forEach((f) => f.classList.remove("has-error"));
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN");
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function statusBadgeClass(status) {
  const map = {
    "Chờ duyệt": "badge-pending",
    "Đã chấp nhận": "badge-accepted",
    "Từ chối": "badge-rejected",
    "Sắp diễn ra": "badge-upcoming",
    "Đang diễn ra": "badge-ongoing",
    "Đã kết thúc": "badge-ended",
    "Đã hủy": "badge-cancelled",
    "Đã hoàn thành": "badge-accepted",
    "Chưa hoàn thành": "badge-pending",
  };
  return map[status] || "badge-pending";
}

function badge(status) {
  return `<span class="badge ${statusBadgeClass(status)}">${status}</span>`;
}

function logout() {
  Session.clear();
  location.href = "index.html";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
