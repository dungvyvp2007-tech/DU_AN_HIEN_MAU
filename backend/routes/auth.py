from datetime import datetime, timedelta
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from extensions import db
from models import User, Donor
from validators import validate_register_account, ValidationError
from utils import ok, fail, handle_validation_error

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


@bp.post("/register")
@handle_validation_error
def register():
    """Đăng ký tài khoản Người hiến máu (NHM_BM1).
    Quy định: mã người hiến duy nhất, CCCD và email không trùng lặp."""
    data = request.get_json(silent=True) or {}

    ngay_sinh = validate_register_account(data)

    errors = {}
    if User.query.filter_by(username=data["username"].strip()).first():
        errors["username"] = "Tên đăng nhập đã tồn tại."
    if User.query.filter_by(email=data["email"].strip().lower()).first():
        errors["email"] = "Email đã được sử dụng bởi tài khoản khác."
    if Donor.query.filter_by(so_cccd=data["so_cccd"].strip()).first():
        errors["so_cccd"] = "Số CCCD đã tồn tại trong hệ thống."
    if errors:
        raise ValidationError(errors)

    user = User(
        username=data["username"].strip(),
        email=data["email"].strip().lower(),
        role="NHM",
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()  # lấy user.id trước khi tạo donor

    donor = Donor(
        user_id=user.id,
        ho_ten=data["ho_ten"].strip(),
        ngay_sinh=ngay_sinh,
        gioi_tinh=data["gioi_tinh"],
        so_cccd=data["so_cccd"].strip(),
        so_dien_thoai=data["so_dien_thoai"].strip(),
        email=data["email"].strip().lower(),
        nhom_mau=data["nhom_mau"],
    )
    db.session.add(donor)
    db.session.commit()

    return ok({"user": user.to_dict(), "donor": donor.to_dict()},
              "Đăng ký tài khoản thành công. Vui lòng đăng nhập.", 201)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return fail("Vui lòng nhập tên đăng nhập và mật khẩu.", 400)

    user = User.query.filter(
        (User.username == username) | (User.email == username.lower())
    ).first()

    if not user:
        return fail("Tên đăng nhập hoặc mật khẩu không đúng.", 401)

    if user.locked_until and user.locked_until > datetime.utcnow():
        phut = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
        return fail(f"Tài khoản đang tạm khóa do đăng nhập sai nhiều lần. Thử lại sau {phut} phút.", 423)

    if not user.is_active:
        return fail("Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.", 403)

    if not user.check_password(password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)
            user.failed_login_attempts = 0
            db.session.commit()
            return fail(f"Sai mật khẩu quá {MAX_FAILED_ATTEMPTS} lần. Tài khoản bị khóa {LOCK_MINUTES} phút.", 423)
        db.session.commit()
        return fail("Tên đăng nhập hoặc mật khẩu không đúng.", 401)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    extra_claims = {"role": user.role, "username": user.username}
    token = create_access_token(identity=str(user.id), additional_claims=extra_claims)

    payload = {"access_token": token, "user": user.to_dict()}
    if user.role == "NHM" and user.donor_profile:
        payload["donor"] = user.donor_profile.to_dict()

    return ok(payload, "Đăng nhập thành công.")


@bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return fail("Không tìm thấy tài khoản.", 404)
    payload = {"user": user.to_dict()}
    if user.role == "NHM" and user.donor_profile:
        payload["donor"] = user.donor_profile.to_dict()
    return ok(payload)


@bp.post("/change-password")
@jwt_required()
def change_password():
    data = request.get_json(silent=True) or {}
    user = User.query.get(int(get_jwt_identity()))
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not user.check_password(old_password):
        return fail("Mật khẩu hiện tại không đúng.", 400)

    from validators import v_password
    err = v_password(new_password)
    if err:
        return fail(err, 422, errors={"new_password": err})

    user.set_password(new_password)
    db.session.commit()
    return ok(message="Đổi mật khẩu thành công.")
