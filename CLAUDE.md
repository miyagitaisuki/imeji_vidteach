# CLAUDE.md — imeji_vidteach

Dự án dựng video cá nhân của thầy Quang (IMEJI日本語教室). Trả lời tiếng Việt, ngắn gọn.

## Quy ước
- Style: `remotion-project/src/brand.ts` (primary #2563eb, Be Vietnam Pro + Noto Sans JP, giao diện sáng). Chưa có logo.
- Chuẩn xuất: 1080p/30fps/H.264, âm lượng -14 LUFS. Reel dọc 1080x1920, YouTube ngang 1920x1080.
- Luôn lập bảng phân cảnh + ảnh đại diện và cho người dùng duyệt TRƯỚC khi render cuối.
- Media thô nằm trong `Raw/` (không commit). Nhạc: file trong `Raw/`, nhớ ghi credit (freetouse.com).
- Quy trình mẫu: `docs/prompt-edit-video.md`, `scripts/build_reel.ps1`.

## Bài học (video không lời, ví dụ MEO_COOKIE)
- Clip quay điện thoại có xoay -90° (HEVC); ffmpeg tự xoay khi re-encode. COOKIE4 là VP9 3:4.
- Không có lời: bỏ Whisper/cắt khoảng lặng, dùng `scripts/motion.py` chọn đoạn nhiều chuyển động; bỏ audio gốc.
- Overlay Remotion phải đúng khổ video (1080x1920 cho reel); render ProRes 4444 alpha rồi ffmpeg overlay.
- PATH Windows: sau khi cài winget phải nạp lại PATH trong shell.
- yt-dlp lỗi 403: thêm `--extractor-args "youtube:player_client=web_safari,mweb"`.
- Xin phép trước khi tải file (tên, nguồn, dung lượng).
