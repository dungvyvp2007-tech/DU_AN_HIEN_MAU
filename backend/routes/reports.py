from flask import Blueprint, request
from models import Event
from utils import ok, fail, roles_required

bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@bp.get("/su-kien/<string:ma_su_kien>")
@roles_required("QTV", "CBYT")
def event_report(ma_su_kien):
    """QTV_BM2 - Báo cáo tiến độ sự kiện.
    Tỷ lệ hoàn thành = (Tổng lượng máu đã thu / Chỉ tiêu tiếp nhận) × 100%."""
    event = Event.query.filter_by(ma_su_kien=ma_su_kien).first()
    if not event:
        return fail("Không tìm thấy sự kiện.", 404)

    return ok({
        "ma_su_kien": event.ma_su_kien,
        "ten_su_kien": event.ten_su_kien,
        "chi_tieu_ml": event.chi_tieu_ml,
        "tong_luong_mau_da_thu_ml": event.tong_luong_mau_da_thu(),
        "so_nguoi_hoan_thanh": event.so_nguoi_hoan_thanh(),
        "so_dang_ky": len(event.registrations),
        "ty_le_hoan_thanh": event.ty_le_hoan_thanh(),
        "trang_thai": event.trang_thai,
    })


@bp.get("/tong-hop")
@roles_required("QTV")
def summary_report():
    """Báo cáo tổng hợp lượng máu đã tiếp nhận theo từng sự kiện."""
    events = Event.query.order_by(Event.thoi_gian_bat_dau.desc()).all()
    return ok([
        {
            "ma_su_kien": e.ma_su_kien,
            "ten_su_kien": e.ten_su_kien,
            "trang_thai": e.trang_thai,
            "chi_tieu_ml": e.chi_tieu_ml,
            "tong_luong_mau_da_thu_ml": e.tong_luong_mau_da_thu(),
            "ty_le_hoan_thanh": e.ty_le_hoan_thanh(),
        }
        for e in events
    ])
