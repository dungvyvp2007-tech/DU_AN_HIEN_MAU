from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from extensions import db
from models import Registration, CheckinRecord
from validators import validate_checkin
from utils import ok, fail, roles_required, handle_validation_error

bp = Blueprint("checkin", __name__, url_prefix="/api/checkin")


@bp.post("/<string:ma_dang_ky>")
@roles_required("CBYT")
def check_in(ma_dang_ky):
    """Điểm danh (Check-in). Chỉ áp dụng cho đăng ký đã được QTV phê duyệt."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy đăng ký với mã này.", 404)
    if reg.trang_thai != Registration.STATUS_DA_CHAP_NHAN:
        return fail("Chỉ được điểm danh đối với đăng ký đã được Ban tổ chức phê duyệt.", 400)
    if reg.checkin:
        return fail("Đăng ký này đã được điểm danh trước đó.", 409)

    record = CheckinRecord(
        registration_id=reg.id,
        thoi_gian_checkin=datetime.utcnow(),
        trang_thai=CheckinRecord.STATUS_CHUA_HOAN_THANH,
        ghi_nhan_boi=int(get_jwt_identity()),
    )
    db.session.add(record)
    db.session.commit()
    return ok(record.to_dict(), "Điểm danh thành công. Ghi nhận thời gian có mặt.", 201)


@bp.put("/<string:ma_dang_ky>")
@roles_required("CBYT")
@handle_validation_error
def update_checkin(ma_dang_ky):
    """Ghi nhận kết quả hiến máu: lượng máu tiếp nhận (250/350/450 ml),
    cập nhật trạng thái Hoàn thành và ghi chú y tế nếu cần."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg or not reg.checkin:
        return fail("Người hiến chưa được điểm danh (check-in).", 404)

    data = request.get_json(silent=True) or {}
    validate_checkin(data)

    record = reg.checkin
    record.trang_thai = data["trang_thai"]
    if data.get("luong_mau_ml") is not None:
        record.luong_mau_ml = int(data["luong_mau_ml"])
    if data.get("trang_thai") == CheckinRecord.STATUS_CHUA_HOAN_THANH:
        record.luong_mau_ml = None
    record.ghi_chu_y_te = (data.get("ghi_chu_y_te") or "").strip() or None
    record.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(record.to_dict(), "Cập nhật kết quả hiến máu thành công.")


@bp.get("/<string:ma_dang_ky>")
@roles_required("QTV", "CBYT")
def get_checkin(ma_dang_ky):
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy đăng ký.", 404)
    if not reg.checkin:
        return fail("Người hiến chưa được điểm danh.", 404)
    return ok(reg.checkin.to_dict())
