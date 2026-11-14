"""MCP gateway (stdio) cho imeji_vidteach: Claude điều phối dựng video -> lồng tiếng textts -> câu hỏi Demix (QBank).

Chỉ dùng thư viện chuẩn Python + ffmpeg trên PATH. Không sửa gì ngoài thư mục dự án (work/projects/<tên>/).
Biến môi trường: TEXTTS_API_URL (mặc định http://127.0.0.1:8000), QBANK_URL (mặc định http://127.0.0.1:8765),
VIDTEACH_ROOT (mặc định thư mục cha của mcp/), VIDTEACH_FONT (font cho chữ overlay, tùy chọn).
Giao thức: JSON-RPC 2.0, mỗi dòng một thông điệp trên stdin/stdout; log ra stderr.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("VIDTEACH_ROOT") or Path(__file__).resolve().parent.parent)
PROJECTS = ROOT / "work" / "projects"
TEXTTS = (os.environ.get("TEXTTS_API_URL") or "http://127.0.0.1:8000").rstrip("/")
QBANK = (os.environ.get("QBANK_URL") or "http://127.0.0.1:8765").rstrip("/")
FORMATS = {"reel": (1080, 1920), "youtube": (1920, 1080)}
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
STEPS = ["storyboard", "voice", "draft", "approved", "final", "published"]


class ToolError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def log(*a):
    print(*a, file=sys.stderr, flush=True)


def slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", str(name).strip(), flags=re.UNICODE).strip("_")
    if not s:
        raise ToolError("Tên dự án không hợp lệ")
    return s[:60]


def pdir(name: str) -> Path:
    return PROJECTS / slug(name)


def load(name: str) -> dict:
    f = pdir(name) / "project.json"
    if not f.exists():
        raise ToolError(f"Chưa có dự án '{name}'. Gọi vt_new_project trước.")
    return json.loads(f.read_text(encoding="utf-8"))


def save(p: dict):
    p["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (pdir(p["name"]) / "project.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")


def need_step(p: dict, step: str, why: str):
    if STEPS.index(p["step"]) < STEPS.index(step):
        raise ToolError(f"{why} (bước hiện tại: {p['step']}, cần tối thiểu: {step})")


def http(method: str, url: str, body=None, raw=False, ctype="application/json", timeout=600):
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = r.read()
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            detail = detail.get("error") or detail.get("detail") or detail
        except Exception:
            detail = str(e)
        raise ToolError(f"{url} lỗi {e.code}: {detail}")
    except urllib.error.URLError:
        raise ToolError(f"Không kết nối được {url}. Hãy mở ứng dụng tương ứng trước (textts: server.py, qbank: app.py).")
    return out if raw else (json.loads(out.decode("utf-8")) if out else {})


def ffmpeg(args: list[str], what: str):
    if not shutil.which("ffmpeg"):
        raise ToolError("Không tìm thấy ffmpeg trên PATH")
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise ToolError(f"ffmpeg lỗi ở bước {what}: {r.stderr.strip()[-600:]}")


def probe_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise ToolError(f"Không đọc được thời lượng {path}")


def resolve_media(p: str) -> Path:
    f = Path(p)
    f = f if f.is_absolute() else ROOT / f
    if not f.exists():
        raise ToolError(f"Không thấy file: {f}")
    return f


def storyboard_table(p: dict) -> str:
    w, h = FORMATS[p["format"]]
    rows = ["| # | Clip | Từ (s) | Dài (s) | Chữ trên cảnh |", "|---|---|---|---|---|"]
    for i, s in enumerate(p["scenes"], 1):
        rows.append(f"| {i} | {Path(s['clip']).name} | {s.get('start', 0)} | {s['dur']} | {s.get('text', '')} |")
    total = sum(float(s["dur"]) for s in p["scenes"])
    return f"**{p['name']}** — {p['format']} {w}x{h}, tổng {total:.1f}s, bước: {p['step']}\n\n" + "\n".join(rows)


# ---------------------------------------------------------------- tools
def vt_new_project(a):
    name = slug(a["name"])
    fmt = a.get("format", "reel")
    if fmt not in FORMATS:
        raise ToolError("format phải là reel hoặc youtube")
    scenes = a.get("scenes") or []
    if not scenes:
        raise ToolError("Cần ít nhất 1 cảnh trong scenes")
    clean = []
    for s in scenes:
        clip = resolve_media(s["clip"])
        dur = float(s["dur"])
        if dur <= 0:
            raise ToolError("dur phải > 0")
        clean.append({"clip": str(clip), "start": float(s.get("start", 0)), "dur": dur, "text": s.get("text", "")})
    d = pdir(name)
    if (d / "project.json").exists() and not a.get("overwrite"):
        old = load(name)
        if STEPS.index(old["step"]) >= STEPS.index("approved"):
            raise ToolError("Dự án đã duyệt/xuất; đặt overwrite=true nếu thật sự muốn làm lại")
    d.mkdir(parents=True, exist_ok=True)
    music = a.get("music")
    p = {"name": name, "format": fmt, "scenes": clean, "step": "storyboard",
         "music": str(resolve_media(music["file"])) if music else None,
         "music_credit": (music or {}).get("credit", ""), "music_db": float((music or {}).get("db", -22)),
         "voice": None, "draft": None, "final": None, "approved": None, "published": None}
    save(p)
    return storyboard_table(p) + "\n\nHãy cho thầy duyệt bảng phân cảnh này trước khi dựng."


def vt_make_voice(a):
    """Gọi textts /api/v1/dialogue: kịch bản [1]..[2].. (phần sau '//' là bản dịch Việt nếu bilingual)."""
    p = load(a["project"])
    script = str(a.get("script", "")).strip()
    if not script:
        raise ToolError("script rỗng")
    opts = {"format": "mp3", "slow": False, "worksheet": False, "srt": True, "lufs": -16.0,
            "bilingual": bool(a.get("bilingual", False))}
    if a.get("level"):
        opts["level"] = a["level"]
    body = {"title": p["name"], "filename": p["name"], "script": script,
            "engine": a.get("engine", "voicevox"), "options": opts}
    res = http("POST", TEXTTS + "/api/v1/dialogue", body)
    folder = Path(res.get("folder", ""))
    files = res.get("files") or []
    names = [f if isinstance(f, str) else (f.get("path") or f.get("name") or "") for f in files]
    mp3 = next((folder / Path(n).name for n in names if n.endswith(".mp3") and "_slow" not in n), None)
    srt = next((folder / Path(n).name for n in names if n.endswith(".srt") and "_slow" not in n), None)
    if not mp3 or not mp3.exists():
        raise ToolError(f"textts không trả file mp3 hợp lệ: {names}")
    d = pdir(p["name"])
    shutil.copy2(mp3, d / "voice.mp3")
    if srt and srt.exists():
        shutil.copy2(srt, d / "voice.srt")
    p["voice"] = {"script": script, "duration_s": res.get("duration_s"), "has_srt": bool(srt and srt.exists()),
                  "credits": res.get("credits", [])}
    (d / "script.txt").write_text(script, encoding="utf-8")
    p["step"] = "voice" if STEPS.index(p["step"]) < STEPS.index("voice") else p["step"]
    save(p)
    return {"ok": True, "voice": str(d / "voice.mp3"), "duration_s": res.get("duration_s"), "srt": p["voice"]["has_srt"],
            "credits": res.get("credits", [])}


def _build(p: dict, out: Path, draft: bool):
    w, h = FORMATS[p["format"]]
    if draft:
        w, h = w // 2, h // 2
    d = pdir(p["name"])
    voice = d / "voice.mp3"
    scenes = p["scenes"]
    total = sum(s["dur"] for s in scenes)
    inputs, f = [], []
    for i, s in enumerate(scenes):
        inputs += ["-ss", str(s["start"]), "-t", str(s["dur"]), "-i", s["clip"]]
        chain = (f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=white,"
                 f"setsar=1,fps=30,setpts=PTS-STARTPTS")
        if s.get("text"):
            font = os.environ.get("VIDTEACH_FONT")
            txt = str(s["text"]).replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")
            ff = f":fontfile='{font}'" if font else ""
            chain += (f",drawtext=text='{txt}'{ff}:fontcolor=white:fontsize={int(h*0.04)}:box=1:boxcolor=0x2563eb@0.85:"
                      f"boxborderw=14:x=(w-text_w)/2:y=h*0.12")
        f.append(chain + f"[v{i}]")
    n = len(scenes)
    f.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[base]")
    vlabel = "base"
    srt = d / "voice.srt"
    if srt.exists() and p["voice"]:
        sp = str(srt).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        f.append(f"[base]subtitles='{sp}':force_style='FontSize={int(h*0.022)},Outline=2,MarginV={int(h*0.08)}'[sub]")
        vlabel = "sub"
    ai = n
    amix = []
    if p["voice"]:
        inputs += ["-i", str(voice)]
        amix.append(f"[{ai}:a]apad,atrim=0:{total}[vo]")
        ai += 1
    if p["music"]:
        inputs += ["-stream_loop", "-1", "-i", p["music"]]
        amix.append(f"[{ai}:a]atrim=0:{total},volume={p['music_db']}dB,afade=t=in:d=0.5,afade=t=out:st={max(total-1.5,0)}:d=1.5[bg]")
        ai += 1
    if not amix:
        raise ToolError("Chưa có âm thanh: cần vt_make_voice hoặc nhạc nền")
    f += amix
    labels = "".join(f"[{x}]" for x in (["vo"] if p["voice"] else []) + (["bg"] if p["music"] else []))
    cnt = (1 if p["voice"] else 0) + (1 if p["music"] else 0)
    f.append(f"{labels}amix=inputs={cnt}:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    ffmpeg([*inputs, "-filter_complex", ";".join(f), "-map", f"[{vlabel}]", "-map", "[a]", "-t", str(total),
            "-c:v", "libx264", "-crf", "30" if draft else "18", "-preset", "veryfast" if draft else "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], "render")


def vt_render_draft(a):
    p = load(a["project"])
    need_step(p, "storyboard", "Chưa có dự án")
    out = pdir(p["name"]) / "draft.mp4"
    _build(p, out, draft=True)
    p["draft"] = str(out)
    if STEPS.index(p["step"]) < STEPS.index("draft"):
        p["step"] = "draft"
    p["approved"] = None  # dựng lại bản nháp thì phải duyệt lại
    if p["step"] in ("approved", "final", "published"):
        p["step"] = "draft"
    save(p)
    return {"ok": True, "draft": str(out), "duration_s": round(probe_duration(out), 2),
            "next": "Cho thầy xem bảng phân cảnh + bản nháp, rồi gọi vt_approve khi thầy xác nhận."}


def vt_approve(a):
    """CHỈ gọi sau khi thầy đã xem bản nháp và xác nhận bằng lời."""
    p = load(a["project"])
    need_step(p, "draft", "Chưa có bản nháp để duyệt")
    if a.get("user_confirmed") is not True:
        raise ToolError("Cần user_confirmed=true, chỉ đặt khi thầy đã xác nhận rõ ràng")
    if not p.get("draft") or not Path(p["draft"]).exists():
        raise ToolError("Không thấy file bản nháp, render lại bản nháp")
    p["approved"] = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "note": a.get("note", "")}
    p["step"] = "approved"
    save(p)
    return {"ok": True, "approved": p["approved"]}


def vt_render_final(a):
    p = load(a["project"])
    need_step(p, "approved", "Chưa được duyệt: không render bản cuối")
    out = pdir(p["name"]) / "final.mp4"
    _build(p, out, draft=False)
    p["final"] = str(out)
    p["step"] = "final"
    save(p)
    credit = p.get("music_credit") or ""
    return {"ok": True, "final": str(out), "duration_s": round(probe_duration(out), 2),
            "credits": ([credit] if credit else []) + (p["voice"] or {}).get("credits", [])}


def vt_publish_questions(a):
    """Trích audio từ video cuối, đẩy lên QBank (Demix) và tạo câu hỏi nháp. Claude soạn sẵn câu hỏi song ngữ."""
    p = load(a["project"])
    need_step(p, "final", "Phải render bản cuối (sau khi duyệt) trước khi đẩy sang Demix")
    if not p.get("approved"):
        raise ToolError("Chưa được duyệt")
    qs = a.get("questions") or []
    if not qs:
        raise ToolError("Cần danh sách questions")
    chapter = int(a["chapter_id"])
    d = pdir(p["name"])
    mp3 = d / "qbank_audio.mp3"
    ffmpeg(["-i", p["final"], "-vn", "-ac", "1", "-b:a", "96k", str(mp3)], "trích audio")
    raw = mp3.read_bytes()
    if len(raw) > 15 * 1024 * 1024:
        raise ToolError("Audio > 15MB, QBank không nhận; rút ngắn video")
    up = http("POST", QBANK + "/api/media?" + urllib.parse.urlencode({"name": f"{p['name']}.mp3"}), raw,
              ctype="application/octet-stream")
    media = [{"kind": up["kind"], "file": up["file"], "name": up["name"]}]
    transcript = (p["voice"] or {}).get("script", "")
    created, errors = [], []
    for i, q in enumerate(qs, 1):
        body = {"chapter_id": chapter, "bloom": q.get("bloom", 1), "qtype": q.get("qtype", "TN"),
                "content": q["content"], "options": q.get("options", []), "answer": q.get("answer", ""),
                "solution": q.get("solution", ""), "transcript": transcript, "translation": q.get("translation", ""),
                "tags": f"vidteach,{p['name']}", "status": "nhap", "media": media}
        try:
            r = http("POST", QBANK + "/api/questions", body)
            created.append({"id": r.get("id"), "code": r.get("code"), "warnings": r.get("warnings", [])})
        except ToolError as e:
            errors.append({"index": i, "error": str(e)})
    p["published"] = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "created": created, "errors": errors, "media": up["file"]}
    if created:
        p["step"] = "published"
    save(p)
    return {"ok": not errors, "created": created, "errors": errors,
            "note": "Câu hỏi ở trạng thái Nháp trong Demix/QBank; video gốc vẫn ở " + p["final"]}


def vt_status(a):
    if not a.get("project"):
        names = sorted(x.parent.name for x in PROJECTS.glob("*/project.json")) if PROJECTS.exists() else []
        return {"projects": names}
    p = load(a["project"])
    return {"step": p["step"], "table": storyboard_table(p), "voice": p["voice"], "draft": p["draft"],
            "approved": p["approved"], "final": p["final"], "published": p["published"]}


def vt_check_services(_a):
    out = {}
    for k, u in (("textts", TEXTTS + "/api/v1/health"), ("qbank", QBANK + "/api/version")):
        try:
            http("GET", u, timeout=4)
            out[k] = "ok"
        except ToolError as e:
            out[k] = str(e)
    out["ffmpeg"] = "ok" if shutil.which("ffmpeg") else "thiếu"
    return out


def _schema(props, req):
    return {"type": "object", "properties": props, "required": req}


S = {"type": "string"}
TOOLS = [
    ("vt_check_services", "Kiểm tra textts, QBank (Demix) và ffmpeg có sẵn sàng không.", _schema({}, []), vt_check_services),
    ("vt_new_project", "Tạo dự án + bảng phân cảnh (scenes: clip, start, dur, text). format reel (1080x1920) hoặc youtube (1920x1080). "
     "music: {file, credit, db}. Trả bảng phân cảnh để thầy duyệt.",
     _schema({"name": S, "format": {"type": "string", "enum": ["reel", "youtube"]},
              "scenes": {"type": "array", "items": _schema({"clip": S, "start": {"type": "number"}, "dur": {"type": "number"}, "text": S}, ["clip", "dur"])},
              "music": _schema({"file": S, "credit": S, "db": {"type": "number"}}, ["file"]), "overwrite": {"type": "boolean"}},
             ["name", "scenes"]), vt_new_project),
    ("vt_make_voice", "Lồng tiếng bằng textts từ kịch bản [1] ... // bản dịch Việt; lấy mp3 + srt về dự án.",
     _schema({"project": S, "script": S, "engine": {"type": "string", "enum": ["voicevox", "aivis", "edge"]}, "level": S,
              "bilingual": {"type": "boolean"}}, ["project", "script"]), vt_make_voice),
    ("vt_render_draft", "Render bản nháp nhỏ (nửa độ phân giải) để thầy duyệt.", _schema({"project": S}, ["project"]), vt_render_draft),
    ("vt_approve", "Ghi nhận thầy đã duyệt (chỉ sau khi thầy xác nhận bằng lời; user_confirmed=true).",
     _schema({"project": S, "user_confirmed": {"type": "boolean"}, "note": S}, ["project", "user_confirmed"]), vt_approve),
    ("vt_render_final", "Render bản cuối 30fps H.264, -14 LUFS. Chỉ chạy sau khi đã duyệt.", _schema({"project": S}, ["project"]), vt_render_final),
    ("vt_publish_questions", "Đẩy audio của video cuối + câu hỏi (song ngữ do Claude soạn) sang QBank/Demix dạng Nháp. "
     "questions: [{content, options[], answer, solution, translation, qtype, bloom}].",
     _schema({"project": S, "chapter_id": {"type": "integer"}, "questions": {"type": "array", "items": {"type": "object"}}},
             ["project", "chapter_id", "questions"]), vt_publish_questions),
    ("vt_status", "Xem trạng thái một dự án (hoặc liệt kê các dự án nếu bỏ project).", _schema({"project": S}, []), vt_status),
]
HANDLERS = {n: h for n, _d, _s, h in TOOLS}
INSTRUCTIONS = ("Quy trình: vt_check_services -> vt_new_project (bảng phân cảnh, thầy duyệt) -> vt_make_voice -> vt_render_draft "
                "-> thầy xem và xác nhận -> vt_approve -> vt_render_final -> soạn câu hỏi song ngữ Nhật–Việt -> vt_publish_questions. "
                "Không bỏ qua bước duyệt; lỗi ở bước nào thì báo và chạy lại đúng bước đó (file trung gian được giữ).")


def handle(msg: dict):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        v = msg.get("params", {}).get("protocolVersion")
        return {"protocolVersion": v if v in PROTOCOLS else PROTOCOLS[0], "capabilities": {"tools": {}},
                "serverInfo": {"name": "vidteach", "version": "0.1.0"}, "instructions": INSTRUCTIONS}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s} for n, d, s, _h in TOOLS]}
    if method == "tools/call":
        prm = msg.get("params", {})
        h = HANDLERS.get(prm.get("name"))
        if not h:
            return {"content": [{"type": "text", "text": "Tool không tồn tại"}], "isError": True}
        try:
            r = h(prm.get("arguments") or {})
            txt = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, indent=1)
            return {"content": [{"type": "text", "text": txt}]}
        except ToolError as e:
            return {"content": [{"type": "text", "text": f"Lỗi: {e}"}], "isError": True}
        except KeyError as e:
            return {"content": [{"type": "text", "text": f"Thiếu tham số: {e}"}], "isError": True}
        except (ValueError, TypeError) as e:
            return {"content": [{"type": "text", "text": f"Tham số sai: {e}"}], "isError": True}
    raise LookupError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:  # notification
            continue
        try:
            res = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except LookupError:
            res = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Method not found"}}
        except Exception as e:  # noqa: BLE001
            log("lỗi nội bộ:", repr(e))
            res = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
