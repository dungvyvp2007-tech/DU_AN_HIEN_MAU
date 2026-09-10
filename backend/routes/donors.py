from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from extensions import db
from models import User, Donor
from validators import (
    ValidationError, v_ho_ten, v_gioi_tinh, v_phone, v_nhom_mau, v_ngay_sinh,
)
from utils import ok, fail, roles_required, handle_validation_error

bp = Blueprint("donors", __name__, url_prefix="/api/donors")


def _current_donor():
    user_id = int(get_jwt_identity())
    return Donor.query.filter_by(user_id=user_id).first()


@bp.get("/me")
@roles_required("NHM")
def get_my_profile():
    donor = _current_donor()
    if not donor:
        return fail("Không tìm thấy hồ sơ người hiến máu.", 404)
    return ok(donor.to_dict())


@bp.put("/me")
@roles_required("NHM")
@handle_validation_error
def update_my_profile():
    """Cho phép người hiến cập nhật thông tin cá nhân không định danh
    (họ tên, giới tính, SĐT, nhóm máu). CCCD và email không được sửa qua API này
    để tránh trùng lặp / giả mạo danh tính — cần quy trình xác minh riêng."""
    donor = _current_donor()
    if not donor:
        return fail("Không tìm thấy hồ sơ người hiến máu.", 404)

    data = request.get_json(silent=True) or {}
    errors = {}
    for field, validator in (("ho_ten", v_ho_ten), ("gioi_tinh", v_gioi_tinh),
                              ("so_dien_thoai", v_phone), ("nhom_mau", v_nhom_mau)):
        if field in data:
            err = validator(data[field])
            if err:
                errors[field] = err
    if errors:
        raise ValidationError(errors)

    if "ho_ten" in data:
        donor.ho_ten = data["ho_ten"].strip()
    if "gioi_tinh" in data:
        donor.gioi_tinh = data["gioi_tinh"]
    if "so_dien_thoai" in data:
        donor.so_dien_thoai = data["so_dien_thoai"].strip()
    if "nhom_mau" in data:
        donor.nhom_mau = data["nhom_mau"]

    db.session.commit()
    return ok(donor.to_dict(), "Cập nhật hồ sơ thành công.")


@bp.get("")
@roles_required("QTV", "CBYT")
def list_donors():
    """QTV/CBYT tra cứu danh sách người hiến máu, hỗ trợ tìm theo mã, tên, CCCD."""
    q = (request.args.get("q") or "").strip()
    query = Donor.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Donor.ma_nguoi_hien.ilike(like), Donor.ho_ten.ilike(like), Donor.so_cccd.ilike(like))
        )
    page = max(int(request.args.get("page", 1)), 1)
    per_page = 5
    pag = query.order_by(Donor.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return ok({
        "items": [d.to_dict() for d in pag.items],
        "total": pag.total, "page": page, "per_page": per_page, "pages": pag.pages,
    })


@bp.get("/<string:ma_nguoi_hien>")
@roles_required("QTV", "CBYT")
def get_donor(ma_nguoi_hien):
    donor = Donor.query.filter_by(ma_nguoi_hien=ma_nguoi_hien).first()
    if not donor:
        return fail("Không tìm thấy người hiến máu với mã này.", 404)
    latest = donor.latest_medical_declaration()
    data = donor.to_dict()
    data["khai_bao_y_te_gan_nhat"] = latest.to_dict() if latest else None
    return ok(data)
