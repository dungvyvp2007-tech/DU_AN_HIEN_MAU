import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Bảo mật ---
    # Trong môi trường thật, PHẢI đặt biến môi trường SECRET_KEY / JWT_SECRET_KEY
    # riêng, không dùng giá trị mặc định bên dưới.
    SECRET_KEY = os.environ.get("SECRET_KEY", "gdfgdgdfhdhdhdhdgfgdgdfgdgdfgdgđhghfhfgstgr")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "qRrưergdsfg45gtdfgdhfgj")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ["headers"]

    # --- Cơ sở dữ liệu ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'blood_donation.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Tài khoản quản trị viên khởi tạo sẵn ---
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@hienmau.vn")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")

    # --- Quy tắc nghiệp vụ ---
    MIN_AGE_HIEN_MAU = 18
    MAX_AGE_HIEN_MAU = 60
    MIN_CAN_NANG_KG = 45
    MIN_KHOANG_CACH_HIEN_TUAN = 12  # tuần
