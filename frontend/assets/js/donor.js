requireRole("NHM");

let donorState = null;
let medDeclarations = [];
let myRegs = [];
let medPage = 1;
let eventPage = 1;
let myRegPage = 1;
let overviewRegPage = 1;

// ---------------------------------------------------------------- Tabs
document.querySelectorAll(".nav-item[data-tab]").forEach((item) => {
  item.addEventListener("click", () => switchTab(item.dataset.tab));
});

function switchTab(tab) {
  document.querySelectorAll(".nav-item[data-tab]").forEach((i) => i.classList.toggle("active", i.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tab}`));
}

// ---------------------------------------------------------------- Load data
async function loadAll() {
  try {
    const me = await api("/auth/me");
    donorState = me.donor;
    fillProfile();
  } catch (err) { toast(err.message, "error"); }

  try {
    medDeclarations = await api("/medical-declarations/me");
    renderMedHistory();
  } catch (err) { /* ignore if none */ }

  try {
    myRegs = await api("/registrations/me");
    renderMyRegistrations();
    renderOverview();
  } catch (err) { toast(err.message, "error"); }

  loadEvents();
}

function fillProfile() {
  if (!donorState) return;
  document.getElementById("p_ma").value = donorState.ma_nguoi_hien;
  document.getElementById("p_tuoi").value = donorState.tuoi;
  document.getElementById("p_ho_ten").value = donorState.ho_ten;
  document.getElementById("p_gioi_tinh").value = donorState.gioi_tinh;
  document.getElementById("p_nhom_mau").value = donorState.nhom_mau;
  document.getElementById("p_sdt").value = donorState.so_dien_thoai;
  document.getElementById("p_cccd").value = donorState.so_cccd;
  document.getElementById("p_email").value = donorState.email;
}

function renderOverview() {
  const daKhaiBao = medDeclarations.length > 0;
  const soChoDuyet = myRegs.filter((r) => r.trang_thai === "Chờ duyệt").length;
  const soDaChapNhan = myRegs.filter((r) => r.trang_thai === "Đã chấp nhận").length;

  document.getElementById("overviewStats").innerHTML = `
    <div class="stat-feature">
      <div>
        <div class="label">Mã người hiến máu</div>
        <div class="value">${donorState ? donorState.ma_nguoi_hien : "—"}</div>
      </div>
      <div class="sub">Nhóm máu ${donorState ? donorState.nhom_mau : "—"} · ${donorState ? donorState.tuoi : "—"} tuổi</div>
    </div>
    <div class="stat-card"><div class="label">Khai báo y tế</div><div class="value">${daKhaiBao ? "Đã có" : "Chưa có"}</div></div>
    <div class="stat-card"><div class="label">Đang chờ duyệt</div><div class="value">${soChoDuyet}</div></div>
    <div class="stat-card"><div class="label">Đã chấp nhận</div><div class="value">${soDaChapNhan}</div></div>
  `;

  const recent = paginateList(myRegs, overviewRegPage);
  overviewRegPage = recent.page;
  document.getElementById("overviewRegistrations").innerHTML = myRegs.length
    ? `${renderRegTable(recent.items)}${renderPagination(recent.page, recent.pages, recent.total)}`
    : `<div class="empty-state">Bạn chưa có đăng ký nào. Hãy khai báo y tế rồi chọn một sự kiện để tham gia.</div>`;
  document.querySelectorAll("#overviewRegistrations button[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      overviewRegPage = Number(button.dataset.page);
      renderOverview();
    });
  });
}

// ---------------------------------------------------------------- Hồ sơ
document.getElementById("profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const alertBox = document.getElementById("profileAlert");
  const successBox = document.getElementById("profileSuccess");
  alertBox.classList.remove("show");
  successBox.classList.remove("show");
  clearFormErrors(form);

  try {
    const updated = await api("/donors/me", {
      method: "PUT",
      body: {
        ho_ten: document.getElementById("p_ho_ten").value.trim(),
        gioi_tinh: document.getElementById("p_gioi_tinh").value,
        nhom_mau: document.getElementById("p_nhom_mau").value,
        so_dien_thoai: document.getElementById("p_sdt").value.trim(),
      },
    });
    donorState = updated;
    successBox.textContent = "Đã lưu thay đổi hồ sơ.";
    successBox.classList.add("show");
    renderOverview();
  } catch (err) {
    alertBox.textContent = err.message;
    alertBox.classList.add("show");
    if (err.errors) showFormErrors(form, err.errors);
  }
});

// ---------------------------------------------------------------- Khai báo y tế
document.getElementById("m_da_hien").addEventListener("change", (e) => {
  document.getElementById("ngayHienWrap").style.display = e.target.checked ? "block" : "none";
});

document.getElementById("medForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const alertBox = document.getElementById("medAlert");
  const successBox = document.getElementById("medSuccess");
  alertBox.classList.remove("show");
  successBox.classList.remove("show");
  clearFormErrors(form);

  const daHien = document.getElementById("m_da_hien").checked;
  try {
    await api("/medical-declarations", {
      method: "POST",
      body: {
        chieu_cao_cm: document.getElementById("m_cc").value,
        can_nang_kg: document.getElementById("m_cn").value,
        tinh_trang_suc_khoe: document.getElementById("m_ttsk").value.trim(),
        tien_su_benh_ly: document.getElementById("m_tsbl").value.trim(),
        da_hien_12_tuan: daHien,
        ngay_hien_gan_nhat: daHien ? document.getElementById("m_ngay_hien").value : null,
      },
    });
    successBox.textContent = "Đã gửi khai báo y tế thành công. Bạn có thể đăng ký sự kiện.";
    successBox.classList.add("show");
    form.reset();
    document.getElementById("ngayHienWrap").style.display = "none";
    medDeclarations = await api("/medical-declarations/me");
    renderMedHistory();
    renderOverview();
  } catch (err) {
    alertBox.textContent = err.message;
    alertBox.classList.add("show");
    if (err.errors) showFormErrors(form, err.errors);
  }
});

function renderMedHistory() {
  const box = document.getElementById("medHistory");
  if (!medDeclarations.length) {
    box.innerHTML = `<div class="empty-state">Chưa có bản khai báo y tế nào.</div>`;
    return;
  }
  const paged = paginateList(medDeclarations, medPage);
  medPage = paged.page;
  box.innerHTML = `<table><thead><tr>
      <th>Ngày khai báo</th><th>Chiều cao</th><th>Cân nặng</th><th>Đã hiến trong 12 tuần</th>
    </tr></thead><tbody>
    ${paged.items.map((d) => `<tr>
      <td>${fmtDateTime(d.created_at)}</td>
      <td>${d.chieu_cao_cm} cm</td>
      <td>${d.can_nang_kg} kg</td>
      <td>${d.da_hien_12_tuan ? "Có" : "Chưa"}</td>
    </tr>`).join("")}
    </tbody></table>${renderPagination(paged.page, paged.pages, paged.total)}`;
  box.querySelectorAll("button[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      medPage = Number(button.dataset.page);
      renderMedHistory();
    });
  });
}

// ---------------------------------------------------------------- Sự kiện
async function loadEvents() {
  const box = document.getElementById("eventList");
  try {
    const events = await api("/events");
    if (!events.length) {
      box.innerHTML = `<div class="empty-state">Hiện chưa có sự kiện hiến máu nào.</div>`;
      return;
    }
    const registeredEventIds = new Set(myRegs.map((r) => r.event_id));
    const paged = paginateList(events, eventPage);
    eventPage = paged.page;
    box.innerHTML = paged.items.map((ev) => {
      const daDangKy = registeredEventIds.has(ev.id);
      const trangThaiMoDangKy = ev.trang_thai === "Sắp diễn ra" || ev.trang_thai === "Đang diễn ra";
      const coTheDangKy = ev.dang_nhan_dang_ky && trangThaiMoDangKy && !daDangKy;
      return `<div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
          <div>
            <h3 style="margin-bottom:0.2rem;">${escapeHtml(ev.ten_su_kien)}</h3>
            <p style="margin-bottom:0.5rem;">${escapeHtml(ev.dia_diem)}</p>
            <p style="margin-bottom:0;">${fmtDateTime(ev.thoi_gian_bat_dau)} → ${fmtDateTime(ev.thoi_gian_ket_thuc)}</p>
          </div>
          <div style="text-align:right;">
            ${badge(ev.trang_thai)}
            <div style="margin-top:0.6rem;">
              ${daDangKy
                ? `<span class="badge badge-accepted">Đã đăng ký</span>`
                : `<button class="btn btn-primary btn-sm" ${coTheDangKy ? "" : "disabled"} title="${coTheDangKy ? "Đăng ký tham gia" : "Sự kiện đã đóng đăng ký"}" data-event="${ev.ma_su_kien}">Đăng ký tham gia</button>`}
            </div>
          </div>
        </div>
      </div>`;
    }).join("");
    box.insertAdjacentHTML("beforeend", renderPagination(paged.page, paged.pages, paged.total));

    box.querySelectorAll("button[data-event]").forEach((b) => {
      b.addEventListener("click", () => registerForEvent(b.dataset.event, b));
    });
    box.querySelectorAll("button[data-page]").forEach((button) => {
      button.addEventListener("click", () => {
        eventPage = Number(button.dataset.page);
        loadEvents();
      });
    });
  } catch (err) {
    box.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

async function registerForEvent(maSuKien, btn) {
  btn.disabled = true;
  btn.textContent = "Đang đăng ký...";
  try {
    await api("/registrations", { method: "POST", body: { ma_su_kien: maSuKien } });
    toast("Đăng ký tham gia thành công. Vui lòng chờ duyệt.", "success");
    myRegs = await api("/registrations/me");
    renderMyRegistrations();
    renderOverview();
    loadEvents();
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
    btn.textContent = "Đăng ký tham gia";
  }
}

// ---------------------------------------------------------------- Đăng ký của tôi
function renderRegTable(list) {
  return `<table><thead><tr>
      <th>Mã đăng ký</th><th>Sự kiện</th><th>Thời gian đăng ký</th><th>Trạng thái</th><th>Lý do (nếu từ chối)</th>
    </tr></thead><tbody>
    ${list.map((r) => `<tr>
      <td>${r.ma_dang_ky}</td>
      <td>${escapeHtml(r.su_kien.ten_su_kien)}</td>
      <td>${fmtDateTime(r.thoi_gian_dang_ky)}</td>
      <td>${badge(r.trang_thai)}</td>
      <td>${r.ly_do_tu_choi ? escapeHtml(r.ly_do_tu_choi) : "—"}</td>
    </tr>`).join("")}
    </tbody></table>`;
}

function renderMyRegistrations() {
  const box = document.getElementById("myRegistrations");
  const paged = paginateList(myRegs, myRegPage);
  myRegPage = paged.page;
  box.innerHTML = myRegs.length
    ? `${renderRegTable(paged.items)}${renderPagination(paged.page, paged.pages, paged.total)}`
    : `<div class="empty-state">Bạn chưa có đăng ký nào.</div>`;
  box.querySelectorAll("button[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      myRegPage = Number(button.dataset.page);
      renderMyRegistrations();
    });
  });
}

loadAll();
