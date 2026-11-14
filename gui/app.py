"""GUI web local cho vidteach (chỉ thầy dùng). Chạy: python gui/app.py  -> mở http://127.0.0.1:8770

Stdlib thuần, tái sử dụng các handler trong mcp/vidteach_mcp.py. Việc dài (lồng tiếng, render, đẩy Demix)
chạy nền, client hỏi trạng thái qua /api/job. Chỉ phục vụ file trong Raw/ và work/projects/.
"""
from __future__ import annotations

import json
import mimetypes
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp"))
import vidteach_mcp as vt  # noqa: E402

RAW = ROOT / "Raw"
ALLOWED_DIRS = [RAW.resolve(), vt.PROJECTS.resolve()]
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
MEDIA_EXT = {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".ogg"}


def safe_path(p: str) -> Path:
    f = Path(p).resolve()
    if not any(f == d or d in f.parents for d in ALLOWED_DIRS):
        raise vt.ToolError("Đường dẫn nằm ngoài Raw/ và work/projects/")
    if not f.exists():
        raise vt.ToolError(f"Không thấy file: {f.name}")
    return f


def run_job(kind: str, fn, args: dict) -> str:
    jid = uuid.uuid4().hex[:10]
    with JOBS_LOCK:
        JOBS[jid] = {"kind": kind, "state": "running", "log": [f"Bắt đầu: {kind}"], "result": None, "error": None}

    def work():
        try:
            res = fn(args)
            state, out, err = "done", res, None
        except vt.ToolError as e:
            state, out, err = "error", None, str(e)
        except Exception as e:  # noqa: BLE001
            state, out, err = "error", None, f"Lỗi nội bộ: {e}"
            traceback.print_exc()
        with JOBS_LOCK:
            JOBS[jid].update(state=state, result=out, error=err)
            JOBS[jid]["log"].append("Xong." if state == "done" else f"Lỗi: {err}")

    threading.Thread(target=work, daemon=True).start()
    return jid


def list_raw() -> list[dict]:
    if not RAW.exists():
        return []
    out = []
    for f in sorted(RAW.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA_EXT:
            out.append({"path": str(f.relative_to(ROOT)), "name": str(f.relative_to(RAW)), "size_mb": round(f.stat().st_size / 1e6, 1)})
    return out


def list_projects() -> list[dict]:
    out = []
    for f in sorted(vt.PROJECTS.glob("*/project.json")) if vt.PROJECTS.exists() else []:
        p = json.loads(f.read_text(encoding="utf-8"))
        out.append({"name": p["name"], "format": p["format"], "step": p["step"], "updated": p.get("updated", "")})
    return out


def project_detail(name: str) -> dict:
    p = vt.load(name)
    d = vt.pdir(name)

    def media(f: Path) -> str | None:
        return f"/media?path={f}" if f.exists() else None

    return {**p, "steps": vt.STEPS,
            "draft_url": media(Path(p["draft"])) if p.get("draft") else None,
            "final_url": media(Path(p["final"])) if p.get("final") else None,
            "voice_url": media(d / "voice.mp3")}


def services() -> dict:
    return vt.vt_check_services({})


def call_tool(name: str, args: dict) -> str:
    """Chạy tool của gateway; trả về chuỗi kết quả (JSON hoặc bảng)."""
    r = vt.HANDLERS[name](args)
    return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)


INDEX = (Path(__file__).parent / "index.html")


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("[gui] " + (fmt % a) + "\n")

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/state":
                return self._json(200, {"projects": list_projects(), "raw": list_raw(), "services": services()})
            if u.path == "/api/project":
                return self._json(200, project_detail(q["name"]))
            if u.path == "/api/job":
                with JOBS_LOCK:
                    return self._json(200, JOBS.get(q.get("id", ""), {"state": "missing"}))
            if u.path == "/media":
                f = safe_path(q["path"])
                return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self._json(404, {"error": "không có"})
        except vt.ToolError as e:
            self._json(400, {"error": str(e)})

    def do_POST(self):
        u = urlparse(self.path).path
        try:
            b = self._body()
            if u == "/api/new_project":
                return self._json(200, {"text": call_tool("vt_new_project", b)})
            if u == "/api/job/voice":
                return self._json(200, {"job": run_job("Lồng tiếng", lambda a: call_tool("vt_make_voice", a), b)})
            if u == "/api/job/draft":
                return self._json(200, {"job": run_job("Render nháp", lambda a: call_tool("vt_render_draft", a), b)})
            if u == "/api/approve":
                return self._json(200, {"text": call_tool("vt_approve", b)})
            if u == "/api/job/final":
                return self._json(200, {"job": run_job("Render cuối", lambda a: call_tool("vt_render_final", a), b)})
            if u == "/api/job/publish":
                return self._json(200, {"job": run_job("Đẩy Demix", lambda a: call_tool("vt_publish_questions", a), b)})
            self._json(404, {"error": "không có"})
        except vt.ToolError as e:
            self._json(400, {"error": str(e)})
        except (KeyError, ValueError, TypeError) as e:
            self._json(400, {"error": f"Dữ liệu sai: {e}"})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8770), H)
    print("GUI vidteach: http://127.0.0.1:8770", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
