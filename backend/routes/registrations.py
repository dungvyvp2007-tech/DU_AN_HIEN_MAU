from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from extensions import db
from models import Donor, Event, Registration, CheckinRecord
from validators import v_ly_do_tu_choi, validate_checkin, ValidationError
from utils import ok, fail, roles_required, handle_validation_error

bp = Blueprint("registrations", __name__, url_prefix="/api/registrations")


@bp.post("")
@roles_required("NHM")
def create_registration():
    """NHM_BM3 - Đăng ký tham gia sự kiện hiến máu.
    Điều kiện bắt buộc (kiểm tra đầy đủ trước khi ghi):
      1. Tài khoản hợp lệ (đã có hồ sơ người hiến máu).
      2. Đã hoàn thành khai báo y tế (có ít nhất một bản khai).
      3. Sự kiện đang trong thời gian tiếp nhận đăng ký.
      4. Chưa từng đăng ký sự kiện này trước đó.
    """
    donor = Donor.query.filter_by(user_id=int(get_jwt_identity())).first()
    if not donor:
        return fail("Tài khoản chưa có hồ sơ người hiến máu hợp lệ.", 400)

    data = request.get_json(silent=True) or {}
    ma_su_kien = (data.get("ma_su_kien") or "").strip()
    if not ma_su_kien:
        return fail("Vui lòng chọn sự kiện muốn đăng ký.", 400, errors={"ma_su_kien": "Bắt buộc."})

    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)

    latest_declaration = donor.latest_medical_declaration()
    if not latest_declaration:
        return fail("Bạn cần hoàn thành khai báo y tế trước khi đăng ký tham gia sự kiện.", 400)

    if not event.dang_nhan_dang_ky():
        return fail("Sự kiện hiện không trong thời gian tiếp nhận đăng ký.", 400)

    existing = Registration.query.filter_by(donor_id=donor.id, event_id=event.id).first()
    if existing:
        return fail("Bạn đã đăng ký sự kiện này rồi.", 409)

    registration = Registration(
        donor_id=donor.id,
        event_id=event.id,
        medical_declaration_id=latest_declaration.id,
        trang_thai=Registration.STATUS_CHO_DUYET,
    )
    db.session.add(registration)
    db.session.commit()
    return ok(registration.to_dict(), "Đăng ký tham gia hiến máu thành công. Vui lòng chờ duyệt.", 201)


@bp.get("/me")
@roles_required("NHM")
def my_registrations():
    """Tra cứu trạng thái đăng ký theo lịch sử cá nhân."""
    donor = Donor.query.filter_by(user_id=int(get_jwt_identity())).first()
    if not donor:
        return fail("Không tìm thấy hồ sơ người hiến máu.", 404)
    regs = Registration.query.filter_by(donor_id=donor.id).order_by(Registration.thoi_gian_dang_ky.desc()).all()
    return ok([r.to_dict() for r in regs])


@bp.get("/me/<string:ma_dang_ky>")
@roles_required("NHM")
def my_registration_detail(ma_dang_ky):
    """Tra cứu chi tiết một đăng ký theo mã đăng ký."""
    donor = Donor.query.filter_by(user_id=int(get_jwt_identity())).first()
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky, donor_id=donor.id if donor else -1).first()
    if not reg:
        return fail("Không tìm thấy đăng ký với mã này.", 404)
    return ok(reg.to_dict())


@bp.get("")
@roles_required("QTV", "CBYT")
def list_registrations():
    """QTV xét duyệt / CBYT xem để điểm danh. Hỗ trợ lọc theo sự kiện và trạng thái."""
    query = Registration.query
    ma_su_kien = request.args.get("ma_su_kien")
    trang_thai = request.args.get("trang_thai")
    if ma_su_kien:
        event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
        query = query.filter_by(event_id=event.id if event else -1)
    if trang_thai:
        query = query.filter_by(trang_thai=trang_thai)
    regs = query.order_by(Registration.thoi_gian_dang_ky.desc()).all()
    return ok([r.to_dict() for r in regs])


@bp.post("/<string:ma_dang_ky>/duyet")
@roles_required("QTV")
def approve_registration(ma_dang_ky):
    """Xét duyệt dựa trên thông tin khai báo y tế và điều kiện tham gia."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy đăng ký.", 404)
    if reg.trang_thai != Registration.STATUS_CHO_DUYET:
        return fail("Chỉ có thể duyệt các đăng ký đang ở trạng thái Chờ duyệt.", 400)

    donor = reg.donor
    declaration = reg.medical_declaration
    dieu_kien_loi = []
    if donor.tuoi < 18 or donor.tuoi > 60:
        dieu_kien_loi.append("Người hiến không nằm trong độ tuổi 18-60.")
    if declaration.can_nang_kg < 45:
        dieu_kien_loi.append("Cân nặng dưới mức tối thiểu 45kg.")
    if declaration.da_hien_12_tuan:
        dieu_kien_loi.append("Người hiến khai đã hiến máu trong vòng 12 tuần gần đây.")
    if dieu_kien_loi:
        return fail(
            "Người đăng ký chưa đủ điều kiện tham gia hiến máu theo khai báo y tế: " + " ".join(dieu_kien_loi),
            422,
        )

    from datetime import datetime
    reg.trang_thai = Registration.STATUS_DA_CHAP_NHAN
    reg.ly_do_tu_choi = None
    reg.xet_duyet_boi = int(get_jwt_identity())
    reg.thoi_gian_xet_duyet = datetime.utcnow()
    db.session.commit()
    return ok(reg.to_dict(), "Đã chấp nhận đăng ký.")


@bp.post("/<string:ma_dang_ky>/tu-choi")
@roles_required("QTV")
@handle_validation_error
def reject_registration(ma_dang_ky):
    """Từ chối đơn đăng ký — bắt buộc nhập lý do cụ thể."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy đăng ký.", 404)
    if reg.trang_thai != Registration.STATUS_CHO_DUYET:
        return fail("Chỉ có thể từ chối các đăng ký đang ở trạng thái Chờ duyệt.", 400)

    data = request.get_json(silent=True) or {}
    ly_do = data.get("ly_do_tu_choi")
    err = v_ly_do_tu_choi(ly_do)
    if err:
        raise ValidationError({"ly_do_tu_choi": err})

    from datetime import datetime
    reg.trang_thai = Registration.STATUS_TU_CHOI
    reg.ly_do_tu_choi = ly_do.strip()
    reg.xet_duyet_boi = int(get_jwt_identity())
    reg.thoi_gian_xet_duyet = datetime.utcnow()
    db.session.commit()
    return ok(reg.to_dict(), "Đã từ chối đăng ký.")

@bp.get("/results")
@roles_required("QTV", "CBYT")
def get_donation_results():
    """CBYT / QTV xem danh sách các ca hiến máu đã ghi nhận kết quả."""
    q = request.args.get("q", "").strip()

    # Lọc các đăng ký đã có thông tin kết quả (lượng máu / ghi chú / trạng thái hoàn thành)
    query = Registration.query.join(Registration.checkin).filter(
        CheckinRecord.trang_thai.in_(CheckinRecord.ALL_STATUSES)
    )

    if q:
        query = query.join(Registration.donor).filter(
            db.or_(
                Registration.ma_dang_ky.ilike(f"%{q}%"),
                Donor.ho_ten.ilike(f"%{q}%"),
                Donor.ma_nguoi_hien.ilike(f"%{q}%")
            )
        )

    regs = query.order_by(Registration.thoi_gian_dang_ky.desc()).all()
    return ok([r.to_dict() for r in regs])


@bp.put("/<string:ma_dang_ky>/result")
@roles_required("CBYT")
def save_donation_result(ma_dang_ky):
    """CBYT ghi nhận kết quả hiến máu cho lượt đăng ký đã điểm danh."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy thông tin đăng ký.", 404)

    if not reg.checkin:
        return fail("Người hiến chưa được điểm danh (check-in).", 400)

    data = request.get_json(silent=True) or {}
    try:
        validate_checkin(data)
    except ValidationError as error:
        return fail("Dữ liệu kết quả không hợp lệ.", 400, errors=error.errors)

    record = reg.checkin
    record.trang_thai = data["trang_thai"]
    record.luong_mau_ml = int(data["luong_mau_ml"]) if data.get("trang_thai") == CheckinRecord.STATUS_HOAN_THANH else None
    record.ghi_chu_y_te = (data.get("ghi_chu_y_te") or "").strip() or None
    record.updated_at = datetime.utcnow()

    db.session.commit()
    return ok(reg.to_dict(), "Đã lưu kết quả hiến máu thành công.")

@bp.post("/<string:ma_dang_ky>/checkin")
@roles_required("CBYT")
def checkin_registration(ma_dang_ky):
    """CBYT điểm danh người hiến máu khi đến sự kiện."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy thông tin đăng ký.", 404)

    if reg.trang_thai != Registration.STATUS_DA_CHAP_NHAN:
        return fail("Chỉ có thể điểm danh các lượt đăng ký đã được chấp nhận.", 400)

    record = CheckinRecord(
        registration_id=reg.id,
        thoi_gian_checkin=datetime.utcnow(),
        trang_thai=CheckinRecord.STATUS_CHUA_HOAN_THANH,
        ghi_nhan_boi=int(get_jwt_identity()),
    )
    db.session.add(record)
    db.session.commit()
    return ok(reg.to_dict(), "Điểm danh thành công.")


@bp.delete("/<string:ma_dang_ky>")
@roles_required("QTV")
def delete_registration(ma_dang_ky):
    """QTV xóa đơn đăng ký và dữ liệu check-in/kết quả đi kèm."""
    reg = Registration.query.filter_by(ma_dang_ky=ma_dang_ky).first()
    if not reg:
        return fail("Không tìm thấy đăng ký.", 404)

    db.session.delete(reg)
    db.session.commit()
    return ok(None, "Đã xóa đơn đăng ký.")