from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from extensions import db
from models import Event
from validators import validate_event, v_trang_thai_su_kien, ValidationError
from utils import ok, fail, roles_required, handle_validation_error

bp = Blueprint("events", __name__, url_prefix="/api/events")


@bp.post("")
@roles_required("QTV")
@handle_validation_error
def create_event():
    """QTV_BM1 - Tạo sự kiện hiến máu.
    Quy định: thời gian kết thúc phải sau thời gian bắt đầu."""
    data = request.get_json(silent=True) or {}
    bat_dau, ket_thuc = validate_event(data, is_update=False)

    event = Event(
        ten_su_kien=data["ten_su_kien"].strip(),
        dia_diem=data["dia_diem"].strip(),
        thoi_gian_bat_dau=bat_dau,
        thoi_gian_ket_thuc=ket_thuc,
        chi_tieu_ml=int(data["chi_tieu_ml"]),
        trang_thai=Event.STATUS_SAP_DIEN_RA,
        created_by=int(get_jwt_identity()),
    )
    event.cap_nhat_trang_thai_theo_thoi_gian()
    db.session.add(event)
    db.session.commit()
    return ok(event.to_dict(), "Tạo sự kiện thành công.", 201)


@bp.get("")
def list_events():
    """Công khai cho mọi vai trò đã đăng nhập xem danh sách sự kiện."""
    from flask_jwt_extended import verify_jwt_in_request
    verify_jwt_in_request()

    trang_thai = request.args.get("trang_thai")
    events = Event.query.order_by(Event.thoi_gian_bat_dau.desc()).all()
    changed = any(event.cap_nhat_trang_thai_theo_thoi_gian() for event in events)
    if changed:
        db.session.commit()

    events = [event for event in events if not trang_thai or event.trang_thai == trang_thai]
    return ok([e.to_dict(with_stats=True) for e in events])


@bp.get("/<string:ma_su_kien>")
def get_event(ma_su_kien):
    from flask_jwt_extended import verify_jwt_in_request
    verify_jwt_in_request()
    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)
    if event.cap_nhat_trang_thai_theo_thoi_gian():
        db.session.commit()
    return ok(event.to_dict(with_stats=True))


@bp.put("/<string:ma_su_kien>")
@roles_required("QTV")
@handle_validation_error
def update_event(ma_su_kien):
    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)

    data = request.get_json(silent=True) or {}
    merged = {
        "ten_su_kien": data.get("ten_su_kien", event.ten_su_kien),
        "dia_diem": data.get("dia_diem", event.dia_diem),
        "thoi_gian_bat_dau": data.get("thoi_gian_bat_dau", event.thoi_gian_bat_dau.isoformat()),
        "thoi_gian_ket_thuc": data.get("thoi_gian_ket_thuc", event.thoi_gian_ket_thuc.isoformat()),
        "chi_tieu_ml": data.get("chi_tieu_ml", event.chi_tieu_ml),
        "trang_thai": data.get("trang_thai", event.trang_thai),
    }
    bat_dau, ket_thuc = validate_event(merged, is_update=True)

    event.ten_su_kien = merged["ten_su_kien"].strip()
    event.dia_diem = merged["dia_diem"].strip()
    event.thoi_gian_bat_dau = bat_dau
    event.thoi_gian_ket_thuc = ket_thuc
    event.chi_tieu_ml = int(merged["chi_tieu_ml"])
    event.trang_thai = merged["trang_thai"]
    event.cap_nhat_trang_thai_theo_thoi_gian()
    db.session.commit()
    return ok(event.to_dict(with_stats=True), "Cập nhật sự kiện thành công.")


@bp.post("/<string:ma_su_kien>/huy")
@roles_required("QTV")
def cancel_event(ma_su_kien):
    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)
    if event.trang_thai == Event.STATUS_DA_KET_THUC:
        return fail("Không thể hủy sự kiện đã kết thúc.", 400)
    event.trang_thai = Event.STATUS_DA_HUY
    db.session.commit()
    return ok(event.to_dict(), "Đã hủy sự kiện.")


@bp.delete("/<string:ma_su_kien>")
@roles_required("QTV")
def delete_event(ma_su_kien):
    """QTV xóa sự kiện và các đăng ký/check-in liên quan."""
    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)

    db.session.delete(event)
    db.session.commit()
    return ok(None, "Đã xóa sự kiện.")
