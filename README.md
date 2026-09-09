# Hệ thống Hiến máu — Giọt Hồng

Website quản lý hiến máu với 3 vai trò nghiệp vụ theo đúng tài liệu gốc:

| Mã bộ phận | Vai trò | Chức năng chính |
|---|---|---|
| **NHM** | Người hiến máu | Đăng ký tài khoản, khai báo y tế, đăng ký sự kiện, tra cứu trạng thái |
| **QTV** | Quản trị viên / Ban tổ chức | Tạo/quản lý sự kiện, xét duyệt đơn đăng ký, thống kê tiến độ |
| **CBYT** | Cán bộ y tế / Nhân viên điểm hiến | Điểm danh (check-in), ghi nhận kết quả hiến máu |

## Kiến trúc

- **Backend**: Python + Flask, SQLAlchemy (SQLite mặc định, đổi được sang PostgreSQL/MySQL), xác thực JWT, validate chi tiết từng trường ở tầng `validators.py`.
- **Frontend**: HTML/CSS/JS thuần (không cần build), gọi API qua `fetch`.
- **Database**: 6 bảng — `users`, `donors`, `medical_declarations`, `events`, `registrations`, `checkin_records` — ánh xạ đúng 5 biểu mẫu nghiệp vụ (NHM_BM1, NHM_BM2, NHM_BM3, QTV_BM1, QTV_BM2/CBYT_BM1).

```
blood-donation-system/
├── backend/
│   ├── app.py              # Khởi tạo Flask app, đăng ký route, xử lý lỗi
│   ├── config.py           # Cấu hình (đọc từ .env)
│   ├── models.py           # 6 model SQLAlchemy
│   ├── validators.py       # Validate từng trường + từng nghiệp vụ
│   ├── utils.py            # Decorator theo vai trò, response chuẩn hoá
│   ├── seed.py             # Tạo bảng + tài khoản admin mặc định
│   ├── requirements.txt
│   ├── .env.example
│   └── routes/
│       ├── auth.py             # Đăng ký / đăng nhập / đổi mật khẩu
│       ├── donors.py           # Hồ sơ người hiến, tra cứu (QTV/CBYT)
│       ├── medical.py          # Khai báo y tế (NHM_BM2)
│       ├── events.py           # Sự kiện hiến máu (QTV_BM1)
│       ├── registrations.py    # Đăng ký + xét duyệt (NHM_BM3)
│       ├── checkin.py          # Điểm danh + kết quả (CBYT_BM1)
│       └── reports.py          # Báo cáo tiến độ (QTV_BM2)
└── frontend/
    ├── index.html           # Đăng nhập
    ├── dang-ky.html         # Đăng ký người hiến máu
    ├── donor.html + donor.js    # Cổng người hiến máu
    ├── admin.html + admin.js    # Cổng ban tổ chức
    ├── medical.html + medical.js # Cổng cán bộ y tế
    └── assets/css/style.css
```

## Cài đặt & chạy

```bash
cd blood-donation-system/backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # rồi chỉnh SECRET_KEY, JWT_SECRET_KEY, mật khẩu admin

python seed.py                  # tạo cơ sở dữ liệu + tài khoản mẫu
python app.py                   # chạy server tại http://localhost:5000
```

Mở trình duyệt tới `https://he-thong-hien-mau.onrender.com` — backend Flask phục vụ luôn cả frontend tĩnh trong thư mục `frontend/`.



## Quy tắc nghiệp vụ đã được validate ở backend

- **Tài khoản**: username 4-30 ký tự (chữ/số/gạch dưới), mật khẩu ≥ 8 ký tự có chữ và số, khoá tài khoản 15 phút sau 5 lần đăng nhập sai.
- **Người hiến máu**: CCCD đúng 12 số và không trùng, email không trùng, SĐT đúng định dạng Việt Nam, tuổi 18-60, nhóm máu hợp lệ.
- **Khai báo y tế**: chiều cao 100-250cm, cân nặng 1-200kg (cảnh báo nếu dưới 45kg), nếu khai đã hiến trong 12 tuần thì bắt buộc nhập ngày và ngày đó phải thật sự nằm trong 12 tuần gần đây.
- **Đăng ký sự kiện**: chỉ cho đăng ký khi tài khoản hợp lệ + đã khai báo y tế + sự kiện đang mở đăng ký; không cho đăng ký trùng một sự kiện hai lần.
- **Sự kiện**: thời gian kết thúc phải sau thời gian bắt đầu, trạng thái giới hạn trong 4 giá trị quy định.
- **Xét duyệt**: kiểm tra lại điều kiện y tế (tuổi, cân nặng, khoảng cách lần hiến gần nhất) trước khi cho duyệt; từ chối bắt buộc nhập lý do.
- **Điểm danh**: chỉ điểm danh được với đăng ký đã "Đã chấp nhận"; không điểm danh trùng.
- **Kết quả hiến máu**: lượng máu chỉ nhận 250/350/450 ml, bắt buộc khi đánh dấu "Đã hoàn thành".
- **Báo cáo**: tỷ lệ hoàn thành = (tổng lượng máu đã thu / chỉ tiêu tiếp nhận) × 100%, tính tự động từ dữ liệu điểm danh.

## Ghi chú bảo mật khi triển khai thật

1. Đổi `SECRET_KEY`, `JWT_SECRET_KEY` và toàn bộ mật khẩu mặc định.
2. Bật HTTPS, giới hạn CORS về đúng domain frontend (hiện đang mở `*` để dễ phát triển).
3. Chuyển từ SQLite sang PostgreSQL/MySQL cho môi trường sản xuất nhiều người dùng đồng thời.
4. Thiết lập sao lưu định kỳ cơ sở dữ liệu (chứa thông tin CCCD, y tế — dữ liệu nhạy cảm).
