"""
Tầng validate tập trung. Mỗi hàm validate MỘT trường dữ liệu nhỏ nhất,
trả về (is_valid: bool, error_message: str|None). Các hàm validate_* ở cuối
gộp validate từng trường lại thành một dict lỗi {field: message} cho cả form,
để backend luôn kiểm tra kỹ trước khi ghi vào cơ sở dữ liệu.
"""
import re
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+$")
PHONE_RE = re.compile(r"^0\d{9}$")  # SĐT VN: bắt đầu bằng 0, đủ 10 số
CCCD_RE = re.compile(r"^\d{12}$")   # CCCD: đúng 12 chữ số
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,30}$")

VALID_GIOI_TINH = {"Nam", "Nữ", "Khác"}
VALID_NHOM_MAU = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

MIN_AGE = 18
MAX_AGE = 60
MIN_CAN_NANG_KG = 45
MIN_CHIEU_CAO_CM, MAX_CHIEU_CAO_CM = 100, 250
MAX_CAN_NANG_KG = 200
MIN_KHOANG_CACH_TUAN = 12
VALID_VOLUMES_ML = (250, 350, 450)


class ValidationError(Exception):
    """Gói nhiều lỗi field lại, dùng để trả 422 kèm chi tiết từng trường."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__("Dữ liệu không hợp lệ")


# ---------------------------------------------------------------------------
# Hàm validate nguyên tử — mỗi hàm chỉ lo một trường
# ---------------------------------------------------------------------------

def v_required(value, field_label):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return f"{field_label} không được để trống."
    return None


def v_username(value):
    err = v_required(value, "Tên đăng nhập")
    if err:
        return err
    if not USERNAME_RE.match(value):
        return "Tên đăng nhập phải dài 4-30 ký tự, chỉ gồm chữ, số và dấu gạch dưới."
    return None


def v_password(value):
    err = v_required(value, "Mật khẩu")
    if err:
        return err
    if len(value) < 8:
        return "Mật khẩu phải có ít nhất 8 ký tự."
    if not re.search(r"[A-Za-z]", value):
        return "Mật khẩu phải chứa ít nhất một chữ cái."
    if not re.search(r"\d", value):
        return "Mật khẩu phải chứa ít nhất một chữ số."
    return None


def v_email(value):
    err = v_required(value, "Email")
    if err:
        return err
    if not EMAIL_RE.match(value):
        return "Email không đúng định dạng."
    return None


def v_phone(value):
    err = v_required(value, "Số điện thoại")
    if err:
        return err
    if not PHONE_RE.match(value):
        return "Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0."
    return None


def v_cccd(value):
    err = v_required(value, "Số CCCD")
    if err:
        return err
    if not CCCD_RE.match(value):
        return "Số CCCD phải gồm đúng 12 chữ số."
    return None


def v_ho_ten(value):
    err = v_required(value, "Họ và tên")
    if err:
        return err
    if len(value.strip()) < 2 or len(value.strip()) > 100:
        return "Họ và tên phải dài từ 2 đến 100 ký tự."
    if not re.match(r"^[^\d!@#$%^&*()_+=\[\]{};:\"\\|,.<>/?~`]+$", value):
        return "Họ và tên không được chứa số hoặc ký tự đặc biệt."
    return None


def v_ngay_sinh(value_str):
    err = v_required(value_str, "Ngày sinh")
    if err:
        return err, None
    try:
        d = datetime.strptime(value_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "Ngày sinh không hợp lệ, định dạng đúng là YYYY-MM-DD.", None
    if d > date.today():
        return "Ngày sinh không được là ngày trong tương lai.", None
    tuoi = date.today().year - d.year - ((date.today().month, date.today().day) < (d.month, d.day))
    if tuoi < MIN_AGE:
        return f"Người hiến máu phải từ {MIN_AGE} tuổi trở lên.", None
    if tuoi > MAX_AGE:
        return f"Người hiến máu không được quá {MAX_AGE} tuổi.", None
    return None, d


def v_gioi_tinh(value):
    err = v_required(value, "Giới tính")
    if err:
        return err
    if value not in VALID_GIOI_TINH:
        return f"Giới tính phải là một trong: {', '.join(VALID_GIOI_TINH)}."
    return None


def v_nhom_mau(value):
    err = v_required(value, "Nhóm máu")
    if err:
        return err
    if value not in VALID_NHOM_MAU:
        return f"Nhóm máu phải là một trong: {', '.join(sorted(VALID_NHOM_MAU))}."
    return None


def v_chieu_cao(value):
    if value is None:
        return "Chiều cao không được để trống."
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "Chiều cao phải là số."
    if f < MIN_CHIEU_CAO_CM or f > MAX_CHIEU_CAO_CM:
        return f"Chiều cao phải trong khoảng {MIN_CHIEU_CAO_CM}-{MAX_CHIEU_CAO_CM} cm."
    return None


def v_can_nang(value):
    if value is None:
        return "Cân nặng không được để trống."
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "Cân nặng phải là số."
    if f <= 0 or f > MAX_CAN_NANG_KG:
        return f"Cân nặng phải trong khoảng 1-{MAX_CAN_NANG_KG} kg."
    if f < MIN_CAN_NANG_KG:
        return f"Cân nặng phải từ {MIN_CAN_NANG_KG} kg trở lên để đủ điều kiện hiến máu."
    return None


def v_tinh_trang_suc_khoe(value):
    return v_required(value, "Tình trạng sức khỏe hiện tại")


def v_ngay_hien_gan_nhat(value_str, da_hien_12_tuan):
    """Nếu có khai đã từng hiến trong 12 tuần, ngày hiến gần nhất là bắt buộc
    và phải thực sự nằm trong vòng 12 tuần trở lại đây."""
    if not da_hien_12_tuan:
        return None, None
    err = v_required(value_str, "Ngày hiến máu gần nhất")
    if err:
        return err, None
    try:
        d = datetime.strptime(value_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "Ngày hiến máu gần nhất không hợp lệ, định dạng đúng là YYYY-MM-DD.", None
    if d > date.today():
        return "Ngày hiến máu gần nhất không được là ngày trong tương lai.", None
    so_ngay = (date.today() - d).days
    if so_ngay > MIN_KHOANG_CACH_TUAN * 7:
        return "Ngày hiến máu gần nhất bạn khai không nằm trong vòng 12 tuần gần đây.", None
    return None, d


def v_ten_su_kien(value):
    err = v_required(value, "Tên sự kiện")
    if err:
        return err
    if len(value.strip()) > 200:
        return "Tên sự kiện không được vượt quá 200 ký tự."
    return None


def v_dia_diem(value):
    err = v_required(value, "Địa điểm tổ chức")
    if err:
        return err
    if len(value.strip()) > 255:
        return "Địa điểm không được vượt quá 255 ký tự."
    return None


def v_datetime(value_str, field_label):
    err = v_required(value_str, field_label)
    if err:
        return err, None
    try:
        dt = datetime.fromisoformat(value_str)
    except (ValueError, TypeError):
        return f"{field_label} không hợp lệ, định dạng đúng là ISO 8601 (YYYY-MM-DDTHH:MM).", None
    return None, dt


def v_chi_tieu_ml(value):
    if value is None:
        return "Chỉ tiêu tiếp nhận không được để trống."
    try:
        i = int(value)
    except (TypeError, ValueError):
        return "Chỉ tiêu tiếp nhận phải là số nguyên."
    if i <= 0:
        return "Chỉ tiêu tiếp nhận phải là số nguyên dương."
    if i > 10_000_000:
        return "Chỉ tiêu tiếp nhận vượt quá giới hạn hợp lý."
    return None


def v_trang_thai_su_kien(value):
    from models import Event
    err = v_required(value, "Trạng thái sự kiện")
    if err:
        return err
    if value not in Event.ALL_STATUSES:
        return f"Trạng thái sự kiện phải là một trong: {', '.join(Event.ALL_STATUSES)}."
    return None


def v_luong_mau_ml(value):
    if value is None:
        return "Lượng máu tiếp nhận không được để trống."
    try:
        i = int(value)
    except (TypeError, ValueError):
        return "Lượng máu tiếp nhận phải là số nguyên."
    if i not in VALID_VOLUMES_ML:
        return f"Lượng máu tiếp nhận chỉ được nhận một trong các mức: {', '.join(str(v) for v in VALID_VOLUMES_ML)} ml."
    return None


def v_ly_do_tu_choi(value):
    return v_required(value, "Lý do từ chối")


def v_ghi_chu_y_te(value, required=False):
    if required:
        return v_required(value, "Ghi chú y tế")
    if value and len(value) > 2000:
        return "Ghi chú y tế không được vượt quá 2000 ký tự."
    return None


# ---------------------------------------------------------------------------
# Hàm validate gộp cho từng nghiệp vụ — dùng trực tiếp trong route
# ---------------------------------------------------------------------------

def validate_register_account(data):
    errors = {}
    for field, validator in (
        ("username", v_username),
        ("password", v_password),
        ("email", v_email),
        ("ho_ten", v_ho_ten),
        ("gioi_tinh", v_gioi_tinh),
        ("so_cccd", v_cccd),
        ("so_dien_thoai", v_phone),
        ("nhom_mau", v_nhom_mau),
    ):
        err = validator(data.get(field))
        if err:
            errors[field] = err

    err, ngay_sinh = v_ngay_sinh(data.get("ngay_sinh"))
    if err:
        errors["ngay_sinh"] = err

    if errors:
        raise ValidationError(errors)
    return ngay_sinh


def validate_medical_declaration(data):
    errors = {}
    err = v_chieu_cao(data.get("chieu_cao_cm"))
    if err:
        errors["chieu_cao_cm"] = err
    err = v_can_nang(data.get("can_nang_kg"))
    if err:
        errors["can_nang_kg"] = err
    err = v_tinh_trang_suc_khoe(data.get("tinh_trang_suc_khoe"))
    if err:
        errors["tinh_trang_suc_khoe"] = err

    da_hien_12_tuan = bool(data.get("da_hien_12_tuan"))
    err, ngay_hien_gan_nhat = v_ngay_hien_gan_nhat(data.get("ngay_hien_gan_nhat"), da_hien_12_tuan)
    if err:
        errors["ngay_hien_gan_nhat"] = err

    if errors:
        raise ValidationError(errors)
    return ngay_hien_gan_nhat


def validate_event(data, is_update=False):
    errors = {}
    err = v_ten_su_kien(data.get("ten_su_kien"))
    if err:
        errors["ten_su_kien"] = err
    err = v_dia_diem(data.get("dia_diem"))
    if err:
        errors["dia_diem"] = err
    err = v_chi_tieu_ml(data.get("chi_tieu_ml"))
    if err:
        errors["chi_tieu_ml"] = err

    err, bat_dau = v_datetime(data.get("thoi_gian_bat_dau"), "Thời gian bắt đầu")
    if err:
        errors["thoi_gian_bat_dau"] = err
    err, ket_thuc = v_datetime(data.get("thoi_gian_ket_thuc"), "Thời gian kết thúc")
    if err:
        errors["thoi_gian_ket_thuc"] = err

    if bat_dau and ket_thuc and ket_thuc <= bat_dau:
        errors["thoi_gian_ket_thuc"] = "Thời gian kết thúc phải sau thời gian bắt đầu."

    if is_update:
        err = v_trang_thai_su_kien(data.get("trang_thai"))
        if err:
            errors["trang_thai"] = err

    if errors:
        raise ValidationError(errors)
    return bat_dau, ket_thuc


def validate_checkin(data):
    errors = {}
    trang_thai = data.get("trang_thai")
    err = v_required(trang_thai, "Trạng thái")
    if err:
        errors["trang_thai"] = err
    from models import CheckinRecord
    if trang_thai and trang_thai not in CheckinRecord.ALL_STATUSES:
        errors["trang_thai"] = f"Trạng thái phải là một trong: {', '.join(CheckinRecord.ALL_STATUSES)}."

    # Lượng máu chỉ bắt buộc khi đánh dấu Đã hoàn thành
    if trang_thai == CheckinRecord.STATUS_HOAN_THANH:
        err = v_luong_mau_ml(data.get("luong_mau_ml"))
        if err:
            errors["luong_mau_ml"] = err
    elif data.get("luong_mau_ml") is not None:
        err = v_luong_mau_ml(data.get("luong_mau_ml"))
        if err:
            errors["luong_mau_ml"] = err

    err = v_ghi_chu_y_te(data.get("ghi_chu_y_te"), required=False)
    if err:
        errors["ghi_chu_y_te"] = err

    if errors:
        raise ValidationError(errors)
