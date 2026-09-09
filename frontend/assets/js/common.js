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

function ensureChangePasswordModal() {
  if (document.getElementById("changePasswordModal")) return;

  const modal = document.createElement("div");
  modal.className = "modal-backdrop";
  modal.id = "changePasswordModal";
  modal.innerHTML = `
    <div class="modal">
      <h3>Đổi mật khẩu</h3>
      <div class="alert alert-error" id="changePasswordAlert"></div>
      <div class="alert alert-success" id="changePasswordSuccess"></div>
      <form id="changePasswordForm" novalidate>
        <div class="field" data-field="old_password">
          <label for="oldPassword">Mật khẩu hiện tại</label>
          <input type="password" id="oldPassword" autocomplete="current-password" required>
          <div class="error-text"></div>
        </div>
        <div class="field" data-field="new_password">
          <label for="newPassword">Mật khẩu mới</label>
          <input type="password" id="newPassword" autocomplete="new-password" required>
          <div class="hint">Tối thiểu 8 ký tự, có chữ và số.</div>
          <div class="error-text"></div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" id="closeChangePassword">Hủy</button>
          <button type="submit" class="btn btn-primary" style="width:auto;" id="changePasswordBtn">Lưu mật khẩu</button>
        </div>
      </form>
    </div>`;
  document.body.appendChild(modal);

  const form = document.getElementById("changePasswordForm");
  const alertBox = document.getElementById("changePasswordAlert");
  const successBox = document.getElementById("changePasswordSuccess");
  const button = document.getElementById("changePasswordBtn");
  const close = () => {
    modal.classList.remove("show");
    form.reset();
    clearFormErrors(form);
    alertBox.classList.remove("show");
    successBox.classList.remove("show");
  };

  document.getElementById("closeChangePassword").addEventListener("click", close);
  modal.addEventListener("click", (event) => { if (event.target === modal) close(); });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormErrors(form);
    alertBox.classList.remove("show");
    successBox.classList.remove("show");
    button.disabled = true;
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: {
          old_password: document.getElementById("oldPassword").value,
          new_password: document.getElementById("newPassword").value,
        },
      });
      Session.clear();
      alert("Đổi mật khẩu thành công.");
      location.replace("index.html");
    } catch (err) {
      alertBox.textContent = err.message;
      alertBox.classList.add("show");
      if (err.errors) showFormErrors(form, err.errors);
    } finally {
      button.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const changePasswordButton = document.getElementById("changePasswordButton");
  if (changePasswordButton) {
    ensureChangePasswordModal();
    changePasswordButton.addEventListener("click", () => {
      document.getElementById("changePasswordModal").classList.add("show");
      document.getElementById("oldPassword").focus();
    });
  }

  if (Session.token) {
    api("/auth/me").then((data) => {
      if (data.user) Session.user = data.user;
    }).catch(() => {});
  }
});
