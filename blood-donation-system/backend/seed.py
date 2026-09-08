"""
Khởi tạo cơ sở dữ liệu và tạo sẵn tài khoản Quản trị viên (QTV).
Chạy: python seed.py
"""
from datetime import date
from app import create_app
from extensions import db
from models import User, Donor

app = create_app()

with app.app_context():
    db.create_all()

    # --- Tài khoản admin (QTV) tạo sẵn ---
    admin_username = app.config["ADMIN_USERNAME"]
    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            email=app.config["ADMIN_EMAIL"],
            role="QTV",
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        print(f"Đã tạo tài khoản quản trị viên: {admin_username} / {app.config['ADMIN_PASSWORD']}")
    else:
        print(f"Tài khoản quản trị viên '{admin_username}' đã tồn tại, bỏ qua.")

    # --- Một tài khoản cán bộ y tế (CBYT) mẫu, để test luồng điểm danh ---
    staff_username = "canbo_yte1"
    staff = User.query.filter_by(username=staff_username).first()
    if not staff:
        staff = User(username=staff_username, email="canbo.yte1@hienmau.vn", role="CBYT")
        staff.set_password("CanBo@123")
        db.session.add(staff)
        print(f"Đã tạo tài khoản cán bộ y tế mẫu: {staff_username} / CanBo@123")

    db.session.commit()
    print("\nHoàn tất khởi tạo cơ sở dữ liệu.")
    print("QUAN TRỌNG: hãy đổi mật khẩu các tài khoản mặc định ngay khi triển khai thật.")
