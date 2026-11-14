# IMEJI Video Teach (imeji_vidteach)

Dựng video cá nhân cho IMEJI日本語教室 bằng Remotion + Hyperframes + FFmpeg + Whisper + yt-dlp.

## Cấu trúc
- `remotion-project/` — template đồ hoạ (phụ đề, lower third, `src/brand.ts` = style IMEJI). `npm i && npm run dev`.
- `hyperframes-project/` — dự án Hyperframes (HTML → MP4). `npm run check`, `npm run render`.
- `scripts/` — phân tích chuyển động, ghép reel.
- `docs/` — prompt mẫu, ví dụ bảng phân cảnh.
- `Raw/`, `Output video/`, `Sample video/`, `work/` — media, KHÔNG đưa lên git.

## Công cụ cần cài (Windows)
`winget install Gyan.FFmpeg yt-dlp.yt-dlp`, `pip install openai-whisper`, Node ≥ 20.
