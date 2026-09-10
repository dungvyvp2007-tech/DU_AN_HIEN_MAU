requireRole("CBYT");

let currentCkFilter = "Đã chấp nhận";

document.querySelectorAll(".nav-item[data-tab]").forEach((item) => {
  item.addEventListener("click", () => switchTab(item.dataset.tab));
});

function switchTab(tab) {
  document.querySelectorAll(".nav-item[data-tab]").forEach((i) => i.classList.toggle("active", i.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${tab}`));
  if (tab === "nguoi-hien") loadDonors();
  if (tab === "results") loadResults();
}

document.querySelectorAll(".ckFilterTab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".ckFilterTab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentCkFilter = btn.dataset.status;
    loadRegistrations();
  });
});

async function loadRegistrations() {
  const wrap = document.getElementById("regWrap");
  try {
    const path = currentCkFilter ? `/registrations?trang_thai=${encodeURIComponent(currentCkFilter)}` : "/registrations";
    const regs = await api(path);
    wrap.innerHTML = regs.length
      ? `<div class="card"><table><thead><tr>
          <th>Mã đăng ký</th><th>Người hiến</th><th>Nhóm máu</th><th>Sự kiện</th><th>Trạng thái đăng ký</th><th>Điểm danh</th><th>Thao tác</th>
        </tr></thead><tbody>
        ${regs.map((r) => `<tr>
          <td><b>${r.ma_dang_ky}</b></td>
          <td>${escapeHtml(r.nguoi_hien ? r.nguoi_hien.ho_ten : "—")}<div class="hint" style="color:var(--muted);font-size:0.78rem;">${r.nguoi_hien ? r.nguoi_hien.ma_nguoi_hien : ""}</div></td>
          <td>${r.nguoi_hien ? r.nguoi_hien.nhom_mau || "—" : "—"}</td>
          <td>${escapeHtml(r.su_kien ? r.su_kien.ten_su_kien : "—")}</td>
          <td>${badge(r.trang_thai)}</td>
          <td><span class="badge ${r.da_diem_danh ? 'badge-success' : 'badge-warning'}">${r.da_diem_danh ? "Đã điểm danh" : "Chưa điểm danh"}</span></td>
          <td>${actionCell(r)}</td>
        </tr>`).join("")}
        </tbody></table></div>`
      : `<div class="empty-state">Không có đăng ký nào phù hợp.</div>`;

    wrap.querySelectorAll("button[data-checkin]").forEach((b) => b.addEventListener("click", () => doCheckin(b.dataset.checkin, b)));
    wrap.querySelectorAll("button[data-result]").forEach((b) => b.addEventListener("click", () => openResultModal(b.dataset.result)));
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

function actionCell(r) {
  if (r.trang_thai === "Chờ duyệt" || r.trang_thai === "Từ chối") return "—";
  
  // Ép kiểu Boolean(r.da_diem_danh) để xử lý cả trường hợp DB trả về true/false hoặc 1/0
  const isCheckedIn = Boolean(r.da_diem_danh);

  if (!isCheckedIn) {
    if (r.trang_thai !== "Đã chấp nhận") return "—";
    return `<button class="btn btn-primary btn-sm" data-checkin="${r.ma_dang_ky}">Điểm danh</button>`;
  }
  if (r.ket_qua) {
    return `<span class="badge badge-success">Đã ghi nhận</span>`;
  }
  
  // Hiện nút Ghi nhận kết quả sau khi đã điểm danh
  return `<button class="btn btn-ghost btn-sm" data-result="${r.ma_dang_ky}">Ghi nhận kết quả</button>`;
}

async function doCheckin(maDangKy, btn) {
  btn.disabled = true;
  try {
    await api(`/registrations/${maDangKy}/checkin`, { method: "POST" });
    toast("Điểm danh thành công! Hãy nhập kết quả hiến máu.", "success");
    
    // Tải lại bảng để cập nhật trạng thái "Đã điểm danh"
    await loadRegistrations(); 
    
    // Tự động mở luôn Modal nhập kết quả hiến máu
    openResultModal(maDangKy);
  } catch (err) {
    toast(err.message || "Lỗi điểm danh không xác định.", "error");
    btn.disabled = false;
  }
}

const resultModal = document.getElementById("resultModal");
const resultForm = document.getElementById("resultForm");
const resultAlert = document.getElementById("resultAlert");

function openResultModal(maDangKy) {
  clearFormErrors(resultForm);
  resultAlert.classList.remove("show");
  resultForm.reset();
  document.getElementById("rs_ma_dang_ky").value = maDangKy;
  document.getElementById("rs_ma_dang_ky_display").textContent = maDangKy;
  toggleLuongMauField();
  resultModal.classList.add("show");
}
if (document.getElementById("closeResultModal")) {
  document.getElementById("closeResultModal").addEventListener("click", () => resultModal.classList.remove("show"));
}

document.getElementById("rs_trangthai").addEventListener("change", toggleLuongMauField);
function toggleLuongMauField() {
  const isHoanThanh = document.getElementById("rs_trangthai").value === "Đã hoàn thành";
  document.getElementById("rs_luongmau_wrap").style.display = isHoanThanh ? "block" : "none";
}

resultForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultAlert.classList.remove("show");
  clearFormErrors(resultForm);
  const maDangKy = document.getElementById("rs_ma_dang_ky").value;
  const trangThai = document.getElementById("rs_trangthai").value;
  try {
    await api(`/registrations/${maDangKy}/result`, {
      method: "PUT",
      body: {
        trang_thai: trangThai,
        luong_mau_ml: trangThai === "Đã hoàn thành" ? Number(document.getElementById("rs_luongmau").value) : null,
        ghi_chu_y_te: document.getElementById("rs_ghichu").value.trim(),
      },
    });
    toast("Đã lưu kết quả hiến máu.", "success");
    resultModal.classList.remove("show");
    await loadRegistrations();
    await loadResults();
  } catch (err) {
    resultAlert.textContent = err.message;
    resultAlert.classList.add("show");
    if (err.errors) showFormErrors(resultForm, err.errors);
  }
});

// Tra cứu người hiến
let donorPage = 1;

async function loadDonors(q = "", page = donorPage) {
  const wrap = document.getElementById("donorTableWrap");
  try {
    donorPage = page;
    const res = await api(`/donors?q=${encodeURIComponent(q)}&page=${page}`);
    wrap.innerHTML = res.items.length
      ? `<div class="card"><table><thead><tr>
          <th>Mã</th><th>Họ tên</th><th>Ngày sinh</th><th>Nhóm máu</th><th>SĐT</th>
        </tr></thead><tbody>
        ${res.items.map((d) => `<tr>
          <td>${d.ma_nguoi_hien}</td><td>${escapeHtml(d.ho_ten)}</td><td>${fmtDate(d.ngay_sinh)}</td>
          <td>${d.nhom_mau}</td><td>${d.so_dien_thoai}</td>
        </tr>`).join("")}
        </tbody></table>${renderPagination(res.page, res.pages, res.total)}</div>`
      : `<div class="empty-state">Không tìm thấy người hiến máu phù hợp.</div>`;
    wrap.querySelectorAll("button[data-page]").forEach((button) => {
      button.addEventListener("click", () => loadDonors(document.getElementById("donorSearch").value.trim(), Number(button.dataset.page)));
    });
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

let donorSearchTimer;
document.getElementById("donorSearch").addEventListener("input", (e) => {
  clearTimeout(donorSearchTimer);
  donorSearchTimer = setTimeout(() => loadDonors(e.target.value.trim(), 1), 350);
});

// Tải danh sách kết quả hiến máu
let resultPage = 1;

async function loadResults(q = "", page = resultPage) {
  const wrap = document.getElementById("resultTableWrap");
  try {
    resultPage = page;
    const res = await api(`/registrations/results?q=${encodeURIComponent(q)}&page=${page}`);
    wrap.innerHTML = res.items.length
      ? `<div class="card"><table><thead><tr>
          <th>Mã ĐK</th>
          <th>Người hiến</th>
          <th>Nhóm máu</th>
          <th>Sự kiện</th>
          <th>Thời gian điểm danh</th>
          <th>Lượng máu</th>
          <th>Kết quả</th>
          <th>Ghi chú y tế</th>
        </tr></thead><tbody>
        ${res.items.map((r) => {
          const ketQua = r.ket_qua || {};
          const luongMau = ketQua.luong_mau_ml ?? r.luong_mau_ml;
          return `<tr>
            <td><b>${r.ma_dang_ky}</b></td>
            <td>${escapeHtml(r.nguoi_hien ? r.nguoi_hien.ho_ten : "—")}<div class="hint" style="color:var(--muted);font-size:0.78rem;">${r.nguoi_hien ? r.nguoi_hien.ma_nguoi_hien : ""}</div></td>
            <td>${r.nguoi_hien ? r.nguoi_hien.nhom_mau || "—" : "—"}</td>
            <td>${escapeHtml(r.su_kien ? r.su_kien.ten_su_kien : "—")}</td>
            <td>${ketQua.thoi_gian_checkin ? fmtDateTime(ketQua.thoi_gian_checkin) : "—"}</td>
            <td><b>${luongMau ? luongMau + " ml" : "—"}</b></td>
            <td>${badge(ketQua.trang_thai || "Chưa có kết quả")}</td>
            <td>${escapeHtml(ketQua.ghi_chu_y_te || r.ghi_chu_y_te || "—")}</td>
          </tr>`;
        }).join("")}
        </tbody></table>${renderPagination(res.page, res.pages, res.total)}</div>`
      : `<div class="empty-state">Chưa có kết quả hiến máu nào.</div>`;
    wrap.querySelectorAll("button[data-page]").forEach((button) => {
      button.addEventListener("click", () => loadResults(document.getElementById("resultSearch").value.trim(), Number(button.dataset.page)));
    });
  } catch (err) {
    wrap.innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

let resultSearchTimer;
document.getElementById("resultSearch").addEventListener("input", (e) => {
  clearTimeout(resultSearchTimer);
  resultSearchTimer = setTimeout(() => loadResults(e.target.value.trim(), 1), 350);
});

loadRegistrations();