# vidteach MCP gateway

Claude điều phối: dựng video (vidteach) → lồng tiếng (textts) → câu hỏi (Demix/QBank).
Chỉ cần Python 3 + ffmpeg. Chạy local qua stdio.

## Cấu hình Claude Desktop
Xem `claude_desktop_config.example.json` (đổi đường dẫn). Trước khi dùng: mở textts (`python server.py`, cổng 8000) và QBank (`python3 app.py`, cổng 8765).

## Quy trình tool
`vt_check_services` → `vt_new_project` (bảng phân cảnh, thầy duyệt) → `vt_make_voice` → `vt_render_draft` → thầy xác nhận → `vt_approve` → `vt_render_final` → Claude soạn câu hỏi song ngữ Nhật–Việt → `vt_publish_questions`.

- `vt_render_final` và `vt_publish_questions` bị chặn nếu chưa `vt_approve`.
- QBank chỉ nhận ảnh/âm thanh (≤15MB), nên video gốc nằm ở `work/projects/<tên>/final.mp4`; QBank nhận audio trích từ video + transcript, câu hỏi ở trạng thái Nháp.
- Lỗi ở bước nào: báo và chạy lại bước đó; file trung gian giữ trong `work/projects/<tên>/` (không commit).
- Credit nhạc (freetouse.com) trả về trong kết quả `vt_render_final`.

Kiểm thử: `python3 mcp/test_e2e.py` (dùng textts/QBank giả + clip tổng hợp).
