from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from extensions import db
from models import Donor, MedicalDeclaration
from validators import validate_medical_declaration
from utils import ok, fail, roles_required, handle_validation_error

bp = Blueprint("medical", __name__, url_prefix="/api/medical-declarations")


@bp.post("")
@roles_required("NHM")
@handle_validation_error
def create_declaration():
    """NHM_BM2 - Người hiến khai báo thông tin y tế.
    Bắt buộc thực hiện trước khi đăng ký tham gia sự kiện hiến máu."""
    donor = Donor.query.filter_by(user_id=int(get_jwt_identity())).first()
    if not donor:
        return fail("Không tìm thấy hồ sơ người hiến máu.", 404)

    data = request.get_json(silent=True) or {}
    ngay_hien_gan_nhat = validate_medical_declaration(data)

    declaration = MedicalDeclaration(
        donor_id=donor.id,
        chieu_cao_cm=float(data["chieu_cao_cm"]),
        can_nang_kg=float(data["can_nang_kg"]),
        tien_su_benh_ly=(data.get("tien_su_benh_ly") or "").strip() or None,
        tinh_trang_suc_khoe=data["tinh_trang_suc_khoe"].strip(),
        da_hien_12_tuan=bool(data.get("da_hien_12_tuan")),
        ngay_hien_gan_nhat=ngay_hien_gan_nhat,
    )
    db.session.add(declaration)
    db.session.commit()
    return ok(declaration.to_dict(), "Khai báo y tế thành công.", 201)


@bp.get("/me")
@roles_required("NHM")
def my_declarations():
    donor = Donor.query.filter_by(user_id=int(get_jwt_identity())).first()
    if not donor:
        return fail("Không tìm thấy hồ sơ người hiến máu.", 404)
    return ok([d.to_dict() for d in donor.medical_declarations])


@bp.get("/donor/<int:donor_id>")
@roles_required("QTV", "CBYT")
def declarations_of_donor(donor_id):
    donor = Donor.query.get(donor_id)
    if not donor:
        return fail("Không tìm thấy người hiến máu.", 404)
    return ok([d.to_dict() for d in donor.medical_declarations])


