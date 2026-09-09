/* Lớp giao tiếp API dùng chung cho toàn bộ frontend. */
const API_BASE = "https://he-thong-hien-mau.onrender.com/api";

function toSessionUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    role: user.role,
    is_active: user.is_active,
  };
}

const Session = {
  get token() { return localStorage.getItem("hienmau_token"); },
  set token(v) { v ? localStorage.setItem("hienmau_token", v) : localStorage.removeItem("hienmau_token"); },
  get user() {
    try {
      const user = toSessionUser(JSON.parse(localStorage.getItem("hienmau_user") || "null"));
      if (user) localStorage.setItem("hienmau_user", JSON.stringify(user));
      return user;
    } catch { return null; }
  },
  set user(v) {
    const user = toSessionUser(v);
    user ? localStorage.setItem("hienmau_user", JSON.stringify(user)) : localStorage.removeItem("hienmau_user");
  },
  clear() { this.token = null; this.user = null; },
};

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && Session.token) headers["Authorization"] = `Bearer ${Session.token}`;

  let res, json;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw { message: "Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối mạng.", status: 0 };
  }

  try {
    json = await res.json();
  } catch {
    json = { success: false, message: "Phản hồi từ máy chủ không hợp lệ." };
  }

  if (res.status === 401 && auth) {
    Session.clear();
    if (!location.pathname.endsWith("index.html") && location.pathname !== "/") {
      location.href = "index.html";
    }
  }

  if (!res.ok || json.success === false) {
    throw { message: json.message || "Đã xảy ra lỗi.", status: res.status, errors: json.errors || {} };
  }
  return json.data;
}

function requireRole(...roles) {
  const user = Session.user;
  if (!Session.token || !user || !roles.includes(user.role)) {
    location.href = "index.html";
  }
  return user;
}
