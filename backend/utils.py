from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from validators import ValidationError


def ok(data=None, message=None, status=200):
    body = {"success": True}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return jsonify(body), status


def fail(message, status=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def roles_required(*allowed_roles):
    """Chặn truy cập nếu vai trò của tài khoản đăng nhập không nằm trong danh sách cho phép."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in allowed_roles:
                return fail("Bạn không có quyền thực hiện thao tác này.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def handle_validation_error(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValidationError as e:
            return fail("Dữ liệu không hợp lệ.", 422, errors=e.errors)
    return wrapper
