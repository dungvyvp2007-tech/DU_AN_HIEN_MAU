import os
from flask import Flask, send_from_directory
from config import Config
from extensions import db, jwt, cors
from utils import fail

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    with app.app_context():
        db.create_all()
        try:
            from seed import run_seed
            run_seed()
        except Exception as e:
            pass

    from routes.auth import bp as auth_bp
    from routes.donors import bp as donors_bp
    from routes.medical import bp as medical_bp
    from routes.events import bp as events_bp
    from routes.registrations import bp as registrations_bp
    from routes.checkin import bp as checkin_bp
    from routes.reports import bp as reports_bp

    for bp in (auth_bp, donors_bp, medical_bp, events_bp, registrations_bp, checkin_bp, reports_bp):
        app.register_blueprint(bp)

    # --- Xử lý lỗi JWT thống nhất ---
    @jwt.unauthorized_loader
    def _missing_token(reason):
        return fail("Bạn cần đăng nhập để thực hiện thao tác này.", 401)

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return fail("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", 401)

    @jwt.expired_token_loader
    def _expired_token(header, payload):
        return fail("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", 401)

    # --- Xử lý lỗi chung ---
    from sqlalchemy.exc import IntegrityError

    @app.errorhandler(IntegrityError)
    def _integrity_error(e):
        db.session.rollback()
        return fail("Dữ liệu bị trùng lặp hoặc vi phạm ràng buộc cơ sở dữ liệu.", 409)

    @app.errorhandler(404)
    def _not_found(e):
        return fail("Không tìm thấy tài nguyên được yêu cầu.", 404)

    @app.errorhandler(405)
    def _method_not_allowed(e):
        return fail("Phương thức không được hỗ trợ.", 405)

    @app.errorhandler(500)
    def _server_error(e):
        return fail("Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.", 500)

    @app.get("/api/health")
    def health():
        return {"success": True, "message": "Hệ thống hiến máu đang hoạt động."}

    # --- Phục vụ frontend tĩnh (chỉ dùng khi chạy toàn bộ trên một server duy nhất) ---
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:path>")
    def static_files(path):
        full_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIR, path)
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
