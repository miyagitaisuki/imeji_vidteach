"""Kiểm thử end-to-end gateway với textts/QBank giả (stub) và clip tổng hợp bằng ffmpeg. Chạy: python3 mcp/test_e2e.py"""
import json, os, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
(tmp / "tts_out").mkdir()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=300:d=8", str(tmp / "tts_out/v.mp3")], check=True)
(tmp / "tts_out/v.srt").write_text("1\n00:00:00,000 --> 00:00:03,000\nこんにちは\n\n2\n00:00:03,000 --> 00:00:06,000\nXin chào\n", encoding="utf-8")
for i in (1, 2):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=s=640x480:d=6:r=30", "-pix_fmt", "yuv420p", str(tmp / f"c{i}.mp4")], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=120:d=20", str(tmp / "m.mp3")], check=True)
seen = {"q": []}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, o):
        b = json.dumps(o).encode(); self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._j(200, {"ok": True})
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/api/v1/dialogue"):
            return self._j(200, {"ok": True, "folder": str(tmp / "tts_out"), "files": ["v.mp3", "v.srt"], "duration_s": 8, "credits": ["VOICEVOX:test"]})
        if self.path.startswith("/api/media"):
            return self._j(201, {"file": "abc.mp3", "kind": "audio", "name": "x.mp3", "size": len(body)})
        if self.path == "/api/questions":
            seen["q"].append(json.loads(body)); return self._j(201, {"id": len(seen["q"]), "code": f"Q{len(seen['q'])}"})
        self._j(404, {"error": "no"})

srv = HTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
env = {**os.environ, "TEXTTS_API_URL": f"http://127.0.0.1:{port}", "QBANK_URL": f"http://127.0.0.1:{port}", "VIDTEACH_ROOT": str(tmp)}
proc = subprocess.Popen([sys.executable, str(Path(__file__).parent / "vidteach_mcp.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
_id = [0]
def rpc(method, params=None):
    _id[0] += 1
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": _id[0], "method": method, "params": params or {}}) + "\n"); proc.stdin.flush()
    return json.loads(proc.stdout.readline())["result"]
def call(tool, **a):
    r = rpc("tools/call", {"name": tool, "arguments": a}); return r.get("isError", False), r["content"][0]["text"]
def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: sys.exit(1)

rpc("initialize", {"protocolVersion": "2025-06-18"})
ok(len(rpc("tools/list")["tools"]) == 8, "R1 liệt kê 8 tool")
sc = [{"clip": str(tmp / "c1.mp4"), "start": 0, "dur": 3, "text": "Chao: Neko"}, {"clip": str(tmp / "c2.mp4"), "start": 1, "dur": 3}]
for fmt in ("reel", "youtube"):
    e, t = call("vt_new_project", name="t_" + fmt, format=fmt, scenes=sc, music={"file": str(tmp / "m.mp3"), "credit": "freetouse.com"})
    ok(not e and "| 1 |" in t, f"R2 bảng phân cảnh {fmt}")
e, t = call("vt_render_final", project="t_reel"); ok(e, "R5 không render cuối khi chưa duyệt")
e, t = call("vt_publish_questions", project="t_reel", chapter_id=1, questions=[{"content": "q"}]); ok(e and not seen["q"], "R5 không đẩy Demix khi chưa duyệt")
e, t = call("vt_make_voice", project="t_reel", script="[1] こんにちは // Xin chào", bilingual=True); ok(not e, "R3 TTS lấy mp3+srt: " + t[:60])
e, t = call("vt_render_draft", project="t_reel"); ok(not e, "R2 bản nháp: " + t[:80])
e, t = call("vt_approve", project="t_reel", user_confirmed=False); ok(e, "R5 approve cần user_confirmed")
e, t = call("vt_approve", project="t_reel", user_confirmed=True); ok(not e, "R5 approve")
e, t = call("vt_render_final", project="t_reel"); ok(not e and "freetouse.com" in t, "R9 final + credit")
fin = tmp / "work/projects/t_reel/final.mp4"
pr = lambda s: subprocess.run(["ffprobe", "-v", "error", "-select_streams", s[0], "-show_entries", s[1], "-of", "csv=p=0", str(fin)], capture_output=True, text=True).stdout.strip()
ok(pr(("v", "stream=width,height")) == "1080,1920", "R2 reel 1080x1920")
lu = subprocess.run(["ffmpeg", "-i", str(fin), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
i_val = float(lu.rsplit("I:", 1)[1].split("LUFS")[0]); ok(-16 < i_val < -12, f"R3 độ to {i_val} LUFS ~ -14")
e, t = call("vt_publish_questions", project="t_reel", chapter_id=1, questions=[{"content": "Q1 / Câu 1", "options": ["a", "b"], "answer": "a", "translation": "vi"}]); ok(not e and len(seen["q"]) == 1 and seen["q"][0]["status"] == "nhap", "R6 câu hỏi nháp tạo trong QBank")
e, t = call("vt_make_voice", project="t_youtube", script="[1] x"); ok(not e, "voice youtube")
e, t = call("vt_render_draft", project="t_youtube"); ok(not e, "draft youtube")
srv.shutdown(); srv.server_close()
e, t = call("vt_make_voice", project="t_youtube", script="[1] x"); ok(e and "Không kết nối" in t, "R7 lỗi dịch vụ báo rõ, project còn nguyên")
ok((tmp / "work/projects/t_youtube/draft.mp4").exists(), "R7 giữ file trung gian")
print("ALL PASS")
