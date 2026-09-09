import uuid
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


def _uid(prefix):
    """Sinh mã định danh ngắn, có tiền tố theo bộ phận nghiệp vụ."""
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# TÀI KHOẢN ĐĂNG NHẬP
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # NHM = Người hiến máu, QTV = Quản trị viên/Ban tổ chức, CBYT = Cán bộ y tế
    role = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    donor_profile = db.relationship("Donor", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


# ---------------------------------------------------------------------------
# 1. BỘ PHẬN NGƯỜI HIẾN MÁU (NHM)
# ---------------------------------------------------------------------------
class Donor(db.Model):
    """NHM_BM1 - Phiếu đăng ký thông tin người hiến máu."""

    __tablename__ = "donors"

    id = db.Column(db.Integer, primary_key=True)
    ma_nguoi_hien = db.Column(db.String(20), unique=True, nullable=False, default=lambda: _uid("NHM"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    ho_ten = db.Column(db.String(100), nullable=False)
    ngay_sinh = db.Column(db.Date, nullable=False)
    gioi_tinh = db.Column(db.String(10), nullable=False)  # Nam / Nữ / Khác
    so_cccd = db.Column(db.String(12), unique=True, nullable=False, index=True)
    so_dien_thoai = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    nhom_mau = db.Column(db.String(5), nullable=False)  # A+, A-, B+, B-, AB+, AB-, O+, O-

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medical_declarations = db.relationship("MedicalDeclaration", backref="donor", cascade="all, delete-orphan",
                                            order_by="MedicalDeclaration.created_at.desc()")
    registrations = db.relationship("Registration", backref="donor", cascade="all, delete-orphan")

    @property
    def tuoi(self):
        today = date.today()
        return today.year - self.ngay_sinh.year - (
            (today.month, today.day) < (self.ngay_sinh.month, self.ngay_sinh.day)
        )

    def latest_medical_declaration(self):
        return self.medical_declarations[0] if self.medical_declarations else None

    def to_dict(self):
        return {
            "id": self.id,
            "ma_nguoi_hien": self.ma_nguoi_hien,
            "ho_ten": self.ho_ten,
            "ngay_sinh": self.ngay_sinh.isoformat(),
            "tuoi": self.tuoi,
            "gioi_tinh": self.gioi_tinh,
            "so_cccd": self.so_cccd,
            "so_dien_thoai": self.so_dien_thoai,
            "email": self.email,
            "nhom_mau": self.nhom_mau,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MedicalDeclaration(db.Model):
    """NHM_BM2 - Phiếu khai báo y tế."""

    __tablename__ = "medical_declarations"

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donors.id"), nullable=False)

    chieu_cao_cm = db.Column(db.Float, nullable=False)
    can_nang_kg = db.Column(db.Float, nullable=False)
    tien_su_benh_ly = db.Column(db.Text, nullable=True)
    tinh_trang_suc_khoe = db.Column(db.Text, nullable=False)
    da_hien_12_tuan = db.Column(db.Boolean, nullable=False, default=False)
    ngay_hien_gan_nhat = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "donor_id": self.donor_id,
            "chieu_cao_cm": self.chieu_cao_cm,
            "can_nang_kg": self.can_nang_kg,
            "tien_su_benh_ly": self.tien_su_benh_ly,
            "tinh_trang_suc_khoe": self.tinh_trang_suc_khoe,
            "da_hien_12_tuan": self.da_hien_12_tuan,
            "ngay_hien_gan_nhat": self.ngay_hien_gan_nhat.isoformat() if self.ngay_hien_gan_nhat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 2. BỘ PHẬN QUẢN TRỊ VIÊN / BAN TỔ CHỨC (QTV)
# ---------------------------------------------------------------------------
class Event(db.Model):
    """QTV_BM1 - Phiếu thông tin sự kiện hiến máu."""

    __tablename__ = "events"

    STATUS_SAP_DIEN_RA = "Sắp diễn ra"
    STATUS_DANG_DIEN_RA = "Đang diễn ra"
    STATUS_DA_KET_THUC = "Đã kết thúc"
    STATUS_DA_HUY = "Đã hủy"
    ALL_STATUSES = [STATUS_SAP_DIEN_RA, STATUS_DANG_DIEN_RA, STATUS_DA_KET_THUC, STATUS_DA_HUY]

    id = db.Column(db.Integer, primary_key=True)
    ma_su_kien = db.Column(db.String(20), unique=True, nullable=False, default=lambda: _uid("QTV"))
    ten_su_kien = db.Column(db.String(200), nullable=False)
    dia_diem = db.Column(db.String(255), nullable=False)
    thoi_gian_bat_dau = db.Column(db.DateTime, nullable=False)
    thoi_gian_ket_thuc = db.Column(db.DateTime, nullable=False)
    chi_tieu_ml = db.Column(db.Integer, nullable=False)  # chỉ tiêu lượng máu cần tiếp nhận (ml)
    trang_thai = db.Column(db.String(20), nullable=False, default=STATUS_SAP_DIEN_RA)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    registrations = db.relationship("Registration", backref="event", cascade="all, delete-orphan")

    def tong_luong_mau_da_thu(self):
        total = 0
        for reg in self.registrations:
            if reg.checkin and reg.checkin.trang_thai == CheckinRecord.STATUS_HOAN_THANH:
                total += reg.checkin.luong_mau_ml
        return total

    def so_nguoi_hoan_thanh(self):
        return sum(
            1 for reg in self.registrations
            if reg.checkin and reg.checkin.trang_thai == CheckinRecord.STATUS_HOAN_THANH
        )

    def ty_le_hoan_thanh(self):
        if not self.chi_tieu_ml:
            return 0.0
        return round((self.tong_luong_mau_da_thu() / self.chi_tieu_ml) * 100, 2)

    def dang_nhan_dang_ky(self):
        now = datetime.utcnow()
        return (
            self.trang_thai != Event.STATUS_DA_HUY
            and now <= self.thoi_gian_ket_thuc
        )

    def cap_nhat_trang_thai_theo_thoi_gian(self, now=None):
        """Đồng bộ trạng thái tự động, giữ nguyên sự kiện đã hủy."""
        if self.trang_thai == Event.STATUS_DA_HUY:
            return False

        now = now or datetime.utcnow()
        if now < self.thoi_gian_bat_dau:
            trang_thai_moi = Event.STATUS_SAP_DIEN_RA
        elif now <= self.thoi_gian_ket_thuc:
            trang_thai_moi = Event.STATUS_DANG_DIEN_RA
        else:
            trang_thai_moi = Event.STATUS_DA_KET_THUC

        if self.trang_thai == trang_thai_moi:
            return False
        self.trang_thai = trang_thai_moi
        return True

    def to_dict(self, with_stats=False):
        data = {
            "id": self.id,
            "ma_su_kien": self.ma_su_kien,
            "ten_su_kien": self.ten_su_kien,
            "dia_diem": self.dia_diem,
            "thoi_gian_bat_dau": self.thoi_gian_bat_dau.isoformat(),
            "thoi_gian_ket_thuc": self.thoi_gian_ket_thuc.isoformat(),
            "chi_tieu_ml": self.chi_tieu_ml,
            "trang_thai": self.trang_thai,
            "dang_nhan_dang_ky": self.dang_nhan_dang_ky(),
        }
        if with_stats:
            data.update({
                "tong_luong_mau_da_thu_ml": self.tong_luong_mau_da_thu(),
                "so_nguoi_hoan_thanh": self.so_nguoi_hoan_thanh(),
                "ty_le_hoan_thanh": self.ty_le_hoan_thanh(),
                "so_dang_ky": len(self.registrations),
            })
        return data


class Registration(db.Model):
    """NHM_BM3 - Phiếu đăng ký tham gia hiến máu."""

    __tablename__ = "registrations"

    STATUS_CHO_DUYET = "Chờ duyệt"
    STATUS_DA_CHAP_NHAN = "Đã chấp nhận"
    STATUS_TU_CHOI = "Từ chối"
    ALL_STATUSES = [STATUS_CHO_DUYET, STATUS_DA_CHAP_NHAN, STATUS_TU_CHOI]

    id = db.Column(db.Integer, primary_key=True)
    ma_dang_ky = db.Column(db.String(20), unique=True, nullable=False, default=lambda: _uid("DK"))
    donor_id = db.Column(db.Integer, db.ForeignKey("donors.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    medical_declaration_id = db.Column(db.Integer, db.ForeignKey("medical_declarations.id"), nullable=False)

    thoi_gian_dang_ky = db.Column(db.DateTime, default=datetime.utcnow)
    trang_thai = db.Column(db.String(20), nullable=False, default=STATUS_CHO_DUYET)
    ly_do_tu_choi = db.Column(db.Text, nullable=True)
    xet_duyet_boi = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    thoi_gian_xet_duyet = db.Column(db.DateTime, nullable=True)

    medical_declaration = db.relationship("MedicalDeclaration")
    checkin = db.relationship("CheckinRecord", backref="registration", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("donor_id", "event_id", name="uq_donor_event"),
    )

    def to_dict(self, include_relations=True):
        data = {
            "id": self.id,
            "ma_dang_ky": self.ma_dang_ky,
            "donor_id": self.donor_id,
            "event_id": self.event_id,
            "thoi_gian_dang_ky": self.thoi_gian_dang_ky.isoformat() if self.thoi_gian_dang_ky else None,
            "trang_thai": self.trang_thai,
            "ly_do_tu_choi": self.ly_do_tu_choi,
            "thoi_gian_xet_duyet": self.thoi_gian_xet_duyet.isoformat() if self.thoi_gian_xet_duyet else None,
            "luong_mau_ml": self.checkin.luong_mau_ml if self.checkin else None,
            "ghi_chu_y_te": self.checkin.ghi_chu_y_te if self.checkin else None,
            "ket_qua": self.checkin.to_dict() if self.checkin else None,
        }
        if include_relations:
            data["nguoi_hien"] = {
                "ma_nguoi_hien": self.donor.ma_nguoi_hien,
                "ho_ten": self.donor.ho_ten,
                "nhom_mau": self.donor.nhom_mau,
            }
            data["su_kien"] = {
                "ma_su_kien": self.event.ma_su_kien,
                "ten_su_kien": self.event.ten_su_kien,
            }
            data["da_diem_danh"] = self.checkin is not None
        return data


# ---------------------------------------------------------------------------
# 3. BỘ PHẬN CÁN BỘ Y TẾ / NHÂN VIÊN ĐIỂM HIẾN (CBYT)
# ---------------------------------------------------------------------------
class CheckinRecord(db.Model):
    """CBYT_BM1 - Nhật ký điểm danh và tiếp nhận máu."""

    __tablename__ = "checkin_records"

    STATUS_HOAN_THANH = "Đã hoàn thành"
    STATUS_CHUA_HOAN_THANH = "Chưa hoàn thành"
    ALL_STATUSES = [STATUS_HOAN_THANH, STATUS_CHUA_HOAN_THANH]
    VALID_VOLUMES_ML = (250, 350, 450)

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey("registrations.id"), unique=True, nullable=False)
    thoi_gian_checkin = db.Column(db.DateTime, default=datetime.utcnow)
    luong_mau_ml = db.Column(db.Integer, nullable=True)  # 250 / 350 / 450, có thể null nếu chưa hoàn thành
    trang_thai = db.Column(db.String(20), nullable=False, default=STATUS_CHUA_HOAN_THANH)
    ghi_chu_y_te = db.Column(db.Text, nullable=True)
    ghi_nhan_boi = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "registration_id": self.registration_id,
            "thoi_gian_checkin": self.thoi_gian_checkin.isoformat() if self.thoi_gian_checkin else None,
            "luong_mau_ml": self.luong_mau_ml,
            "trang_thai": self.trang_thai,
            "ghi_chu_y_te": self.ghi_chu_y_te,
        }
