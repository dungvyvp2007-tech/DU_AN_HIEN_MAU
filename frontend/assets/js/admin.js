requireRole("QTV");

let allEvents = [];
let currentRegFilter = "Chờ duyệt";

document.querySelectorAll(".nav-item[data-tab]").forEach((item) => {
  item.addEventListener("click", () => switchTab(item.dataset.tab));
});

function switchTab(tab) {
  document.querySelectorAll(".nav-item[data-tab]").forEach((i) => i.classList.toggle("active", i.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tab}`));
  if (tab === "bao-cao") loadReports();
  if (tab === "nguoi-hien") loadDonors();
}

async function loadAll() {
  await loadEvents();
  await loadOverview();
  await loadRegistrations();
}

// ---------------------------------------------------------------- Tổng quan
async function loadOverview() {
  const tongSuKien = allEvents.length;
  const dangDienRa = allEvents.filter((e) => e.trang_thai === "Đang diễn ra").length;
  const tongThu = allEvents.reduce((s, e) => s + (e.tong_luong_mau_da_thu_ml || 0), 0);
  const tongChiTieu = allEvents.reduce((s, e) => s + e.chi_tieu_ml, 0);
  const tyLe = tongChiTieu ? Math.round((tongThu / tongChiTieu) * 1000) / 10 : 0;

  document.getElementById("overviewStats").innerHTML = `
    <div class="stat-feature">
      <div><div class="label">Tổng lượng máu đã thu (tất cả sự kiện)</div><div class="value">${tongThu.toLocaleString("vi-VN")} ml</div></div>
      <div class="sub">Tỷ lệ hoàn thành trung bình ${tyLe}%</div>
    </div>
    <div class="stat-card"><div class="label">Tổng số sự kiện</div><div class="value">${tongSuKien}</div></div>
    <div class="stat-card"><div class="label">Đang diễn ra</div><div class="value">${dangDienRa}</div></div>
    <div class="stat-card"><div class="label">Chờ duyệt</div><div class="value" id="pendingCount">—</div></div>
  `;

  try {
    const pending = await api("/registrations?trang_thai=Chờ duyệt");
    document.getElementById("pendingCount").textContent = pending.length;
    document.getElementById("overviewPending").innerHTML = pending.length
      ? renderRegTable(pending.slice(0, 6), false)
      : `<div class="empty-state">Không có đơn nào đang chờ duyệt.</div>`;
  } catch (err) { toast(err.message, "error"); }
}

// ---------------------------------------------------------------- Sự kiện
async function loadEvents() {
  const wrap = document.getElementById("eventTableWrap");
  try {
    allEvents = await api("/events");
    if (!allEvents.length) {
      wrap.innerHTML = `<div class="empty-state">Chưa có sự kiện nào. Hãy tạo sự kiện đầu tiên.</div>`;
      return;
    }
    wrap.innerHTML = `<div class="card"><table><thead><tr>
        <th>Mã</th><th>Tên sự kiện</th><th>Thời gian</th><th>Chỉ tiêu</th><th>Đã thu</th><th>Tỷ lệ</th><th>Trạng thái</th><th></th>
      </tr></thead><tbody>
      ${allEvents.map((ev) => `<tr>
        <td>${ev.ma_su_kien}</td>
        <td>${escapeHtml(ev.ten_su_kien)}<div class="hint" style="color:var(--muted);font-size:0.78rem;">${escapeHtml(ev.dia_diem)}</div></td>
        <td>${fmtDateTime(ev.thoi_gian_bat_dau)}<br>→ ${fmtDateTime(ev.thoi_gian_ket_thuc)}</td>
        <td>${ev.chi_tieu_ml.toLocaleString("vi-VN")} ml</td>
        <td>${(ev.tong_luong_mau_da_thu_ml || 0).toLocaleString("vi-VN")} ml</td>
        <td>${ev.ty_le_hoan_thanh}%</td>
        <td>${badge(ev.trang_thai)}</td>
        <td>
          <button class="btn btn-ghost btn-sm" data-edit="${ev.ma_su_kien}">Sửa</button>
          <button class="btn btn-danger btn-sm" data-delete-event="${ev.ma_su_kien}">Xóa</button>
        </td>
      </tr>`).join("")}
      </tbody></table></div>`;

    wrap.querySelectorAll("button[data-edit]").forEach((b) => {
      b.addEventListener("click", () => openEventModal(b.dataset.edit));
    });
    wrap.querySelectorAll("button[data-delete-event]").forEach((b) => {
      b.addEventListener("click", () => openEventDeleteModal(b.dataset.deleteEvent));
    });
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

function openEventDeleteModal(maSuKien) {
  document.getElementById("eventDeleteConfirmMessage").textContent = `Mã sự kiện: ${maSuKien}. Các đơn đăng ký và dữ liệu điểm danh liên quan cũng sẽ bị xóa.`;
  document.getElementById("eventDeleteConfirmModal").dataset.maSuKien = maSuKien;
  document.getElementById("eventDeleteConfirmModal").classList.add("show");
}

const eventDeleteConfirmModal = document.getElementById("eventDeleteConfirmModal");
const eventDeleteConfirmForm = document.getElementById("eventDeleteConfirmForm");

document.getElementById("closeEventDeleteConfirmModal").addEventListener("click", () => {
  eventDeleteConfirmModal.classList.remove("show");
});

eventDeleteConfirmForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const maSuKien = eventDeleteConfirmModal.dataset.maSuKien;
  const btn = [...document.querySelectorAll("button[data-delete-event]")].find((button) => button.dataset.deleteEvent === maSuKien);
  if (!maSuKien || !btn) return;

  btn.disabled = true;
  try {
    await api(`/events/${maSuKien}`, { method: "DELETE" });
    toast("Đã xóa sự kiện.", "success");
    eventDeleteConfirmModal.classList.remove("show");
    await loadEvents();
    await loadRegistrations();
    await loadOverview();
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
  }
});

const eventModal = document.getElementById("eventModal");
const eventForm = document.getElementById("eventForm");
const eventAlert = document.getElementById("eventAlert");

document.getElementById("openCreateEvent").addEventListener("click", () => openEventModal(null));
document.getElementById("closeEventModal").addEventListener("click", () => eventModal.classList.remove("show"));

function toDatetimeLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function openEventModal(maSuKien) {
  clearFormErrors(eventForm);
  eventAlert.classList.remove("show");
  eventForm.reset();
  const ev = maSuKien ? allEvents.find((e) => e.ma_su_kien === maSuKien) : null;

  document.getElementById("eventModalTitle").textContent = ev ? "Sửa sự kiện hiến máu" : "Tạo sự kiện hiến máu";
  document.getElementById("ev_ma_su_kien").value = ev ? ev.ma_su_kien : "";
  document.getElementById("ev_ten").value = ev ? ev.ten_su_kien : "";
  document.getElementById("ev_diadiem").value = ev ? ev.dia_diem : "";
  document.getElementById("ev_batdau").value = ev ? toDatetimeLocal(ev.thoi_gian_bat_dau) : "";
  document.getElementById("ev_ketthuc").value = ev ? toDatetimeLocal(ev.thoi_gian_ket_thuc) : "";
  document.getElementById("ev_chitieu").value = ev ? ev.chi_tieu_ml : "";
  document.getElementById("ev_trangthai_wrap").style.display = ev ? "block" : "none";
  if (ev) document.getElementById("ev_trangthai").value = ev.trang_thai;

  eventModal.classList.add("show");
}

eventForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  eventAlert.classList.remove("show");
  clearFormErrors(eventForm);

  const maSuKien = document.getElementById("ev_ma_su_kien").value;
  const payload = {
    ten_su_kien: document.getElementById("ev_ten").value.trim(),
    dia_diem: document.getElementById("ev_diadiem").value.trim(),
    thoi_gian_bat_dau: document.getElementById("ev_batdau").value,
    thoi_gian_ket_thuc: document.getElementById("ev_ketthuc").value,
    chi_tieu_ml: document.getElementById("ev_chitieu").value,
  };
  if (maSuKien) payload.trang_thai = document.getElementById("ev_trangthai").value;

  try {
    if (maSuKien) {
      await api(`/events/${maSuKien}`, { method: "PUT", body: payload });
      toast("Đã cập nhật sự kiện.", "success");
    } else {
      await api("/events", { method: "POST", body: payload });
      toast("Đã tạo sự kiện mới.", "success");
    }
    eventModal.classList.remove("show");
    await loadEvents();
    await loadOverview();
  } catch (err) {
    eventAlert.textContent = err.message;
    eventAlert.classList.add("show");
    if (err.errors) showFormErrors(eventForm, err.errors);
  }
});

// ---------------------------------------------------------------- Xét duyệt
document.querySelectorAll(".regFilterTab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".regFilterTab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentRegFilter = btn.dataset.status;
    loadRegistrations();
  });
});

function renderRegTable(list, withActions = true) {
  return `<table><thead><tr>
      <th>Mã đăng ký</th><th>Người hiến</th><th>Sự kiện</th><th>Nhóm máu</th><th>Trạng thái</th>${withActions ? "<th></th>" : ""}
    </tr></thead><tbody>
    ${list.map((r) => `<tr>
      <td>${r.ma_dang_ky}</td>
      <td>${escapeHtml(r.nguoi_hien.ho_ten)}<div class="hint" style="color:var(--muted);font-size:0.78rem;">${r.nguoi_hien.ma_nguoi_hien}</div></td>
      <td>${escapeHtml(r.su_kien.ten_su_kien)}</td>
      <td>${r.nguoi_hien.nhom_mau}</td>
      <td>${badge(r.trang_thai)}${r.ly_do_tu_choi ? `<div class="hint" style="color:var(--muted);font-size:0.78rem;">${escapeHtml(r.ly_do_tu_choi)}</div>` : ""}</td>
      ${withActions ? `<td>
        ${r.trang_thai === "Chờ duyệt" ? `
          <button class="btn btn-success btn-sm" data-approve="${r.ma_dang_ky}">Duyệt</button>
          <button class="btn btn-danger btn-sm" data-reject="${r.ma_dang_ky}">Từ chối</button>
        ` : ""}
        <button class="btn btn-danger btn-sm" data-delete="${r.ma_dang_ky}">Xóa</button>
      </td>` : ""}
    </tr>`).join("")}
    </tbody></table>`;
}

async function loadRegistrations() {
  const wrap = document.getElementById("registrationsWrap");
  try {
    const path = currentRegFilter ? `/registrations?trang_thai=${encodeURIComponent(currentRegFilter)}` : "/registrations";
    const regs = await api(path);
    wrap.innerHTML = regs.length
      ? `<div class="card">${renderRegTable(regs)}</div>`
      : `<div class="empty-state">Không có đơn đăng ký nào.</div>`;

    wrap.querySelectorAll("button[data-approve]").forEach((b) => {
      b.addEventListener("click", () => approveRegistration(b.dataset.approve, b));
    });
    wrap.querySelectorAll("button[data-reject]").forEach((b) => {
      b.addEventListener("click", () => openRejectModal(b.dataset.reject));
    });
    wrap.querySelectorAll("button[data-delete]").forEach((b) => {
      b.addEventListener("click", () => deleteRegistration(b.dataset.delete, b));
    });
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

async function deleteRegistration(maDangKy, btn) {
  document.getElementById("deleteConfirmMessage").textContent = `Mã đăng ký: ${maDangKy}. Dữ liệu điểm danh và kết quả đi kèm cũng sẽ bị xóa.`;
  document.getElementById("deleteConfirmModal").dataset.maDangKy = maDangKy;
  document.getElementById("deleteConfirmModal").classList.add("show");
}

const deleteConfirmModal = document.getElementById("deleteConfirmModal");
const deleteConfirmForm = document.getElementById("deleteConfirmForm");

document.getElementById("closeDeleteConfirmModal").addEventListener("click", () => {
  deleteConfirmModal.classList.remove("show");
});

deleteConfirmForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const maDangKy = deleteConfirmModal.dataset.maDangKy;
  const btn = [...document.querySelectorAll("button[data-delete]")].find((button) => button.dataset.delete === maDangKy);
  if (!maDangKy || !btn) return;

  btn.disabled = true;
  try {
    await api(`/registrations/${maDangKy}`, { method: "DELETE" });
    toast("Đã xóa đơn đăng ký.", "success");
    deleteConfirmModal.classList.remove("show");
    await loadRegistrations();
    await loadOverview();
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
  }
});

async function approveRegistration(maDangKy, btn) {
  btn.disabled = true;
  try {
    await api(`/registrations/${maDangKy}/duyet`, { method: "POST" });
    toast("Đã chấp nhận đăng ký.", "success");
    await loadRegistrations();
    await loadOverview();
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
  }
}

const rejectModal = document.getElementById("rejectModal");
const rejectForm = document.getElementById("rejectForm");
const rejectAlert = document.getElementById("rejectAlert");

function openRejectModal(maDangKy) {
  clearFormErrors(rejectForm);
  rejectAlert.classList.remove("show");
  rejectForm.reset();
  document.getElementById("rj_ma_dang_ky").value = maDangKy;
  rejectModal.classList.add("show");
}
document.getElementById("closeRejectModal").addEventListener("click", () => rejectModal.classList.remove("show"));

rejectForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  rejectAlert.classList.remove("show");
  clearFormErrors(rejectForm);
  const maDangKy = document.getElementById("rj_ma_dang_ky").value;
  try {
    await api(`/registrations/${maDangKy}/tu-choi`, {
      method: "POST",
      body: { ly_do_tu_choi: document.getElementById("rj_lydo").value.trim() },
    });
    toast("Đã từ chối đăng ký.", "success");
    rejectModal.classList.remove("show");
    await loadRegistrations();
    await loadOverview();
  } catch (err) {
    rejectAlert.textContent = err.message;
    rejectAlert.classList.add("show");
    if (err.errors) showFormErrors(rejectForm, err.errors);
  }
});

// ---------------------------------------------------------------- Báo cáo
async function loadReports() {
  const wrap = document.getElementById("reportWrap");
  try {
    const data = await api("/reports/tong-hop");
    wrap.innerHTML = data.length
      ? `<div class="card"><table><thead><tr>
          <th>Sự kiện</th><th>Trạng thái</th><th>Chỉ tiêu</th><th>Đã thu</th><th>Tỷ lệ hoàn thành</th>
        </tr></thead><tbody>
        ${data.map((r) => `<tr>
          <td>${escapeHtml(r.ten_su_kien)}</td>
          <td>${badge(r.trang_thai)}</td>
          <td>${r.chi_tieu_ml.toLocaleString("vi-VN")} ml</td>
          <td>${r.tong_luong_mau_da_thu_ml.toLocaleString("vi-VN")} ml</td>
          <td style="min-width:160px;">
            <div class="progress-bar"><div style="width:${Math.min(r.ty_le_hoan_thanh, 100)}%;"></div></div>
            <span class="hint" style="color:var(--muted);">${r.ty_le_hoan_thanh}%</span>
          </td>
        </tr>`).join("")}
        </tbody></table></div>`
      : `<div class="empty-state">Chưa có dữ liệu báo cáo.</div>`;
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

// ---------------------------------------------------------------- Người hiến
async function loadDonors(q = "") {
  const wrap = document.getElementById("donorTableWrap");
  try {
    const res = await api(`/donors?q=${encodeURIComponent(q)}`);
    wrap.innerHTML = res.items.length
      ? `<div class="card"><table><thead><tr>
          <th>Mã</th><th>Họ tên</th><th>Ngày sinh</th><th>Nhóm máu</th><th>SĐT</th><th>CCCD</th>
        </tr></thead><tbody>
        ${res.items.map((d) => `<tr>
          <td>${d.ma_nguoi_hien}</td><td>${escapeHtml(d.ho_ten)}</td><td>${fmtDate(d.ngay_sinh)}</td>
          <td>${d.nhom_mau}</td><td>${d.so_dien_thoai}</td><td>${d.so_cccd}</td>
        </tr>`).join("")}
        </tbody></table></div>`
      : `<div class="empty-state">Không tìm thấy người hiến máu phù hợp.</div>`;
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

let donorSearchTimer;
document.getElementById("donorSearch").addEventListener("input", (e) => {
  clearTimeout(donorSearchTimer);
  donorSearchTimer = setTimeout(() => loadDonors(e.target.value.trim()), 350);
});

loadAll();
